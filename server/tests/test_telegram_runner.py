from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from learnmate.clock import FakeClock
from learnmate.config import Settings
from learnmate.telegram.bot import TelegramRunner, make_telegram_runner
from learnmate.telegram.links import TelegramHooks


def _factory() -> sessionmaker[Session]:
    return sessionmaker()


def test_no_runner_without_token():
    runner = make_telegram_runner(
        Settings(telegram_bot_token=""), _factory(), FakeClock(), TelegramHooks()
    )
    assert runner is None


def test_app_starts_without_bot_token(client: TestClient):
    assert client.app.state.telegram_runner is None
    assert client.get("/api/v1/health").status_code == 200


def test_runner_built_with_token():
    runner = make_telegram_runner(
        Settings(telegram_bot_token="123:fake"),
        _factory(),
        FakeClock(),
        TelegramHooks(),
    )
    assert isinstance(runner, TelegramRunner)
