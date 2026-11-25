import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI

from learnmate.api import (
    assess,
    budget,
    challenges,
    data,
    exams,
    family,
    materials,
    mentor,
    plan,
    presence,
    sessions,
    subjects,
)
from learnmate.auth import install_device_token_auth
from learnmate.backup.job import backup_loop
from learnmate.classroom import ClassroomError
from learnmate.clock import SystemClock
from learnmate.config import Settings, get_settings
from learnmate.db import create_db_engine, make_session_factory
from learnmate.llm import make_llm
from learnmate.llm.budget import BudgetReached
from learnmate.llm.metered import MeteredLlm
from learnmate.presence.watchdog import watchdog_loop
from learnmate.rag.embed import make_embedder
from learnmate.rag.reindex import reindex
from learnmate.rag.rerank import make_reranker
from learnmate.sessions.pins import load_pin_cipher
from learnmate.sessions.service import telegram_new_pin
from learnmate.telegram.bot import make_telegram_runner
from learnmate.telegram.links import TelegramHooks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Best-effort: if the model can't load, the API and Telegram still come up and
    # the stale rows are retried on the next start or by the reindex command.
    try:
        await asyncio.to_thread(
            reindex, app.state.session_factory, app.state.embedder, only_stale=True
        )
    except Exception:
        logging.getLogger(__name__).exception("start-up re-embedding failed")
    runner = app.state.telegram_runner
    if runner is not None:
        await runner.start()
    settings = app.state.settings
    watchdog = (
        asyncio.create_task(
            watchdog_loop(app.state.session_factory, settings, app.state.clock)
        )
        if settings.watchdog_enabled
        else None
    )
    backup = (
        asyncio.create_task(backup_loop(settings, app.state.clock))
        if settings.backup_enabled
        else None
    )
    try:
        yield
    finally:
        if backup is not None:
            backup.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await backup
        if watchdog is not None:
            watchdog.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watchdog
        if runner is not None:
            await runner.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    pin_cipher = load_pin_cipher(settings)
    engine = create_db_engine(settings.database_url)
    app = FastAPI(title="Learnmate", lifespan=lifespan)
    app.state.settings = settings
    app.state.pin_cipher = pin_cipher
    app.state.engine = engine
    clock = SystemClock()
    app.state.clock = clock
    app.state.session_factory = make_session_factory(engine, clock)
    app.state.llm = MeteredLlm(
        make_llm(settings), app.state.session_factory, settings, clock
    )
    app.state.embedder = make_embedder(settings)
    app.state.reranker = make_reranker(settings)
    hooks = TelegramHooks()
    hooks.new_pin = partial(
        telegram_new_pin, settings=settings, clock=clock, cipher=pin_cipher
    )
    app.state.google_transport = None
    app.state.telegram_hooks = hooks
    app.state.telegram_runner = make_telegram_runner(
        settings, app.state.session_factory, clock, hooks
    )

    install_device_token_auth(app, settings.device_token)
    app.include_router(family.router)
    app.include_router(data.router)
    app.include_router(subjects.router)
    app.include_router(materials.router)
    app.include_router(sessions.router)
    app.include_router(presence.router)
    app.include_router(plan.router)
    app.include_router(mentor.router)
    app.include_router(assess.router)
    app.include_router(challenges.router)
    app.include_router(exams.router)
    app.include_router(budget.router)
    app.add_exception_handler(BudgetReached, budget.budget_reached_handler)
    app.add_exception_handler(ClassroomError, materials.classroom_error_handler)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
