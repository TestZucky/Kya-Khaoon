"""
The variety signal must be scoped to ONE user.

Swipe carries no user_id — ownership only exists via
swipe → deck_card → deck → session.user_id. Miss that chain and the query reads
every user's swipes, which is invisible with a single active user and gets worse
the more users you have: someone else's cuisines fill the 3-day window, so the
penalty (-2.0 cuisine / -1.5 style) fires on dishes you've never seen, and
`exclude_ids` removes them from the rules path outright.

Proves: user B's swipes appear in B's signals and never in A's, on all three
returned sets plus the LLM prompt's dish names.

Run:  python -m tests.test_variety_scoping
"""

from tests.dbsetup import fresh_db, use_test_db  # noqa: E402

use_test_db()

from sqlmodel import Session as DBSession  # noqa: E402

from app.db import engine  # noqa: E402
from app.models import (  # noqa: E402
    Deck,
    DeckCard,
    DishConcept,
    Session as MealSession,
    Swipe,
    User,
)
from app.recommend.deck import _recent_names, _recent_signals  # noqa: E402


def _dish(db: DBSession, name: str, cuisine: str, style: str) -> DishConcept:
    dish = DishConcept(
        name=name,
        search_query=name.lower(),
        cuisine=cuisine,
        cooking_style=style,
        is_veg=True,
    )
    db.add(dish)
    db.flush()
    return dish


def _swipe(db: DBSession, user_id: int, dish: DishConcept) -> None:
    """The full ownership chain: session → deck → deck_card → swipe."""
    session = MealSession(user_id=user_id)
    db.add(session)
    db.flush()
    deck = Deck(session_id=session.id)
    db.add(deck)
    db.flush()
    card = DeckCard(deck_id=deck.id, dish_concept_id=dish.id, rank=0, reason="test")
    db.add(card)
    db.flush()
    db.add(Swipe(deck_card_id=card.id, direction="left"))
    db.flush()


def main() -> None:
    fresh_db()

    with DBSession(engine) as db:
        alice = User(device_id="alice")
        bob = User(device_id="bob")
        db.add(alice)
        db.add(bob)
        db.flush()

        # Disjoint on every axis, so any leak is unambiguous.
        biryani = _dish(db, "Chicken Biryani", "North Indian", "rice")
        ramen = _dish(db, "Shoyu Ramen", "Japanese", "noodles")

        _swipe(db, alice.id, biryani)
        _swipe(db, bob.id, ramen)
        db.commit()

        # Plain ints — the ORM instances detach when the session closes.
        biryani_id, ramen_id = biryani.id, ramen.id

        a_cuisines, a_styles, a_ids = _recent_signals(db, alice.id)
        b_cuisines, b_styles, b_ids = _recent_signals(db, bob.id)
        a_names = _recent_names(db, alice.id)
        b_names = _recent_names(db, bob.id)

    print(f"alice: cuisines={a_cuisines} styles={a_styles} names={a_names}")
    print(f"bob:   cuisines={b_cuisines} styles={b_styles} names={b_names}")

    # Each user sees their own swipe — the signal still works.
    assert a_cuisines == {"north indian"}, a_cuisines
    assert a_styles == {"rice"}, a_styles
    assert a_ids == {biryani_id}, a_ids
    assert a_names == ["Chicken Biryani"], a_names
    print("  ok  a user's own swipe reaches their variety signal")

    # And only their own. These are the assertions that fail on an unscoped query.
    assert "japanese" not in a_cuisines, "bob's cuisine leaked into alice's penalty"
    assert "noodles" not in a_styles, "bob's cooking style leaked into alice's penalty"
    assert ramen_id not in a_ids, "bob's dish would be excluded from alice's deck"
    assert "Shoyu Ramen" not in a_names, "bob's dish leaked into alice's LLM prompt"
    print("  ok  another user's swipe never reaches it")

    # Symmetric — not an artefact of insert order or lower ids.
    assert b_cuisines == {"japanese"} and b_styles == {"noodles"}, (b_cuisines, b_styles)
    assert b_ids == {ramen_id} and b_names == ["Shoyu Ramen"], (b_ids, b_names)
    print("  ok  scoping holds in both directions")

    # A user with no swipes gets empty signals, not everyone else's.
    with DBSession(engine) as db:
        empty_cuisines, empty_styles, empty_ids = _recent_signals(db, 9999)
        empty_names = _recent_names(db, 9999)
    assert not empty_cuisines and not empty_styles and not empty_ids
    assert not empty_names
    print("  ok  a user with no history gets an empty signal")

    print("\nVARIETY SCOPING TESTS PASSED ✅")


if __name__ == "__main__":
    main()
