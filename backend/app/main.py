import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_error_handlers
from app.logging_config import setup_logging
from app.middleware import request_context
from app.routers import (
    addresses,
    auth,
    cart,
    decks,
    health,
    profile,
    swiggy_auth,
    swipes,
)

settings = get_settings()
setup_logging(settings.log_level)
log = logging.getLogger("kya.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Nothing creates tables here: migrations own the schema, and the container
    # entrypoint runs `alembic upgrade head` before this process starts.
    log.info(
        "starting · swiggy=%s · dishes=%s",
        settings.swiggy_client,
        "openai" if settings.openai_api_key else "rules-fallback",
    )
    yield


app = FastAPI(title="Kya Khaoon API", version="0.1.0", lifespan=lifespan)

app.middleware("http")(request_context)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(swiggy_auth.router)
app.include_router(addresses.router)
app.include_router(profile.router)
app.include_router(decks.router)
app.include_router(swipes.router)
app.include_router(cart.router)
