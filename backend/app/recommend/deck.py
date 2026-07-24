"""
Deck orchestration: run stage 1, resolve each concept against Swiggy in parallel,
persist the deck, and return cards the frontend can render.

A concept that resolves to no open offer is dropped rather than shown broken, so a
deck may briefly come back short; the caller can widen the concept pool if needed.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlmodel import Session as DBSession
from sqlmodel import select

from app.config import get_settings
from app.errors import UpstreamError
from app.models import (
    Deck,
    DeckCard,
    DishConcept,
    Offer,
    Profile,
    Session,
    Swipe,
)
from app.recommend.concepts import (
    NO_CAP,
    ScoredConcept,
    budget_ceiling,
    select_concepts,
)
from app.recommend.history import OrderInsights, summarize_orders
from app.recommend.llm_concepts import generate_concepts
from app.recommend.resolve import ResolvedOffer, resolve_offer
from app.swiggy.client import SwiggyClient

log = logging.getLogger("kya.deck")

# Ask the model for more dishes than the deck needs, so the deterministic scorer
# has something to choose between. Too close to 5 and ranking is decorative.
LLM_CANDIDATES = 8


class NoPicksError(UpstreamError):
    """Neither stage could produce a deck. The log line says which stage."""


@dataclass
class Card:
    card_id: int
    concept: DishConcept
    offer: Offer
    reason: str
    rank: int


def _rank_llm_picks(
    picks: list[ScoredConcept],
    profile: Profile,
    session: Session,
    *,
    recent_cuisines: set[str],
    recent_styles: set[str],
    limit: int,
) -> list[ScoredConcept]:
    """
    Re-rank the model's candidates with the deterministic scorer and keep the best.

    The LLM's `why` is kept as the card's reason — it's warmer and more specific
    than the rules' generated text. Only the *ordering* comes from scoring, plus
    `select_concepts`' hard-filter pass as one more allergy/diet safety net.

    `exclude_ids` is deliberately not applied: the model already got the recent
    dishes in its prompt, and excluding here could drop us below five cards.
    """
    reasons = {p.concept.id: p.reasons for p in picks}
    ranked = select_concepts(
        [p.concept for p in picks],
        profile,
        session,
        recent_cuisines=recent_cuisines,
        recent_styles=recent_styles,
        limit=limit,
    )
    return [
        ScoredConcept(
            concept=s.concept,
            score=s.score,
            reasons=reasons.get(s.concept.id) or s.reasons,
        )
        for s in ranked
    ]


def _recent_signals(db: DBSession, user_id: int) -> tuple[set[str], set[str], set[int]]:
    """
    What the user has recently seen/rejected — feeds the variety penalty.

    Swipe carries no user_id, so ownership is walked through
    swipe → deck_card → deck → session.user_id. Without that chain the query
    reads every user's swipes: another user's biryani would then suppress North
    Indian in this deck, and `exclude_ids` would drop concepts outright.
    """
    since = datetime.now(timezone.utc) - timedelta(days=3)
    rows = db.exec(
        select(DishConcept.cuisine, DishConcept.cooking_style, DishConcept.id)
        .join(DeckCard, DeckCard.dish_concept_id == DishConcept.id)
        .join(Swipe, Swipe.deck_card_id == DeckCard.id)
        .join(Deck, Deck.id == DeckCard.deck_id)
        .join(Session, Session.id == Deck.session_id)
        .where(Session.user_id == user_id)
        .where(Swipe.created_at >= since)
    ).all()
    cuisines = {r[0].lower() for r in rows}
    styles = {r[1].lower() for r in rows}
    concept_ids = {r[2] for r in rows}
    return cuisines, styles, concept_ids


def _recent_names(db: DBSession, user_id: int, days: int = 3) -> list[str]:
    """Recently-seen dish names, so the LLM can offer variety."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.exec(
        select(DishConcept.name)
        .join(DeckCard, DeckCard.dish_concept_id == DishConcept.id)
        .join(Swipe, Swipe.deck_card_id == DeckCard.id)
        .join(Deck, Deck.id == DeckCard.deck_id)
        .join(Session, Session.id == Deck.session_id)
        .where(Session.user_id == user_id)
        .where(Swipe.created_at >= since)
    ).all()
    return list(dict.fromkeys(rows))  # de-duped, order-preserving


async def _fetch_order_insights(
    client: SwiggyClient, address_id: str, user_token: str | None
) -> OrderInsights:
    """Best-effort: never let a history hiccup block the deck."""
    try:
        orders = await client.get_orders(
            address_id=address_id, limit=20, user_token=user_token
        )
    except Exception as e:  # noqa: BLE001 — history is a nicety, not a requirement
        # Name what the deck loses, so this doesn't read like a harmless blip: a
        # persistent failure here silently drops taste patterns and the
        # just-ordered variety signal from stage 1.
        log.warning(
            "order-history fetch failed (%s); building deck without taste patterns "
            "or the just-ordered variety signal",
            e,
        )
        return OrderInsights(summary=None, recent=[])
    return summarize_orders(orders)


async def _select_stage1(
    db: DBSession,
    profile: Profile,
    session: Session,
    user_id: int,
    insights: OrderInsights,
) -> list[ScoredConcept]:
    """
    LLM generates the dishes when a key is configured; otherwise the deterministic
    rules rank whatever concepts we already know. Either way we get a list of
    persisted concepts + a reason.

    On the LLM path the model is asked for more candidates than we need, and the
    deterministic scorer picks the final five. The model knows what food *is*; the
    scorer is what consistently applies this user's budget, mood, meal time and
    heat tolerance. Asking it to also obey all of that in one shot is where it
    quietly slips — so it proposes, and the rules dispose.
    """
    cuisines, styles, seen_ids = _recent_signals(db, user_id)

    if get_settings().openai_api_key:
        try:
            # Merge swipe-recent and order-recent names into one variety signal.
            recent = list(dict.fromkeys(_recent_names(db, user_id) + insights.recent))
            picks = await generate_concepts(
                db,
                profile,
                session,
                recent,
                order_summary=insights.summary,
                limit=LLM_CANDIDATES,
            )
            if picks:
                return _rank_llm_picks(
                    picks,
                    profile,
                    session,
                    recent_cuisines=cuisines,
                    recent_styles=styles,
                    limit=5,
                )
            log.warning("LLM returned no usable picks; falling back to rules")
        except Exception as e:  # noqa: BLE001 — any LLM failure → rules fallback
            log.warning("LLM pick failed (%s); falling back to rules", e)

    return select_concepts(
        list(db.exec(select(DishConcept)).all()),
        profile,
        session,
        recent_cuisines=cuisines,
        recent_styles=styles,
        exclude_ids=seen_ids,
        limit=5,
    )


async def build_deck(
    db: DBSession,
    client: SwiggyClient,
    *,
    user_id: int,
    address_id: str,
    profile: Profile,
    session: Session,
    sequence: int = 1,
    user_token: str | None = None,
) -> tuple[Deck, list[Card]]:
    # Mine past orders for patterns before picking (order history → smarter deck).
    insights = await _fetch_order_insights(client, address_id, user_token)
    picks = await _select_stage1(db, profile, session, user_id, insights)
    if not picks:
        # Both stage-1 paths came back empty. Nearly always one setup mistake:
        # no OPENAI_API_KEY *and* an unseeded catalogue, so the rules fallback
        # has no dishes to rank. Worth naming — the symptom is an empty deck.
        log.error(
            "stage 1 produced no concepts — set OPENAI_API_KEY, or run `make seed` "
            "to give the rules fallback a catalogue to rank"
        )
        raise NoPicksError("We couldn't put a deck together right now.")

    cap = budget_ceiling(profile, session)  # None when uncapped
    veg_only = profile.diet in {"veg", "vegan", "jain"}

    # Stage 2 for all five concepts at once.
    resolved: list[ResolvedOffer | None] = await asyncio.gather(
        *(
            resolve_offer(
                client,
                address_id=address_id,
                query=p.concept.search_query,
                veg_only=veg_only,
                budget_ceiling=cap or NO_CAP,
                user_token=user_token,
            )
            for p in picks
        )
    )

    deck = Deck(session_id=session.id, sequence=sequence)
    db.add(deck)
    db.flush()  # assign deck.id

    now = datetime.now(timezone.utc)
    cards: list[Card] = []
    rank = 0
    for pick, offer in zip(picks, resolved):
        if offer is None:
            continue  # nothing open for this concept right now
        row = Offer(
            dish_concept_id=pick.concept.id,
            address_id=address_id,
            menu_item_id=offer.menu_item_id,
            restaurant_id=offer.restaurant_id,
            restaurant_name=offer.restaurant_name,
            price=offer.price,
            eta_minutes=offer.eta_minutes,
            rating=offer.rating,
            # Live Swiggy photo when we have one; otherwise the concept's curated
            # image (so the dev/fake path still shows real food, not a placeholder).
            image_url=offer.image_url or pick.concept.image_url or None,
            in_stock=True,
            is_ad=offer.is_ad,
            offer=offer.offer,
            fetched_at=now,
        )
        db.add(row)
        db.flush()

        # The reason is the model's "why" (LLM mode) or the rules reason — both
        # already truthful. Price is shown on the card, so no budget boilerplate.
        reason = pick.reasons[0]

        card = DeckCard(
            deck_id=deck.id,
            dish_concept_id=pick.concept.id,
            offer_id=row.id,
            rank=rank,
            reason=reason,
        )
        db.add(card)
        db.flush()
        cards.append(
            Card(card_id=card.id, concept=pick.concept, offer=row, reason=reason, rank=rank)
        )
        rank += 1

    db.commit()
    return deck, cards
