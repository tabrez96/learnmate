from fastapi import FastAPI

from learnmate.api import data, family
from learnmate.auth import install_device_token_auth
from learnmate.clock import SystemClock
from learnmate.config import Settings, get_settings
from learnmate.db import create_db_engine, make_session_factory
from learnmate.llm import make_llm


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_db_engine(settings.database_url)
    app = FastAPI(title="Learnmate")
    app.state.settings = settings
    app.state.llm = make_llm(settings)
    app.state.engine = engine
    clock = SystemClock()
    app.state.clock = clock
    app.state.session_factory = make_session_factory(engine, clock)

    install_device_token_auth(app, settings.device_token)
    app.include_router(family.router)
    app.include_router(data.router)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
