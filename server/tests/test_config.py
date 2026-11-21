import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from learnmate.config import ModelPrice, Settings, get_settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Settings reads env names case-insensitively, so remove every casing of each field name.
    for key in list(os.environ):
        if key.lower() in Settings.model_fields:
            monkeypatch.delenv(key, raising=False)


def test_defaults() -> None:
    s = Settings()
    assert s.pin_length == 4
    assert s.llm_provider == "anthropic"
    assert s.pin_max_wrong == 5
    assert s.pin_lockout_seconds == 900
    assert s.pin_wrong_before_fallback == 3
    assert s.pin_resend_interval_seconds == 60
    assert s.fallback_max_wrong == 3
    assert s.fallback_lockout_seconds == 3600
    assert s.inactivity_warn_seconds == 240
    assert s.inactivity_lock_seconds == 300
    assert s.grade_bands == {"A": 90, "B": 80, "C": 70, "D": 60, "E": 50, "F": 0}
    assert s.model_main == "claude-sonnet-5-5"
    assert s.model_fast == "claude-haiku-4-5-20251001"
    assert s.embed_model == "BAAI/bge-small-en-v1.5"
    assert s.embed_provider == "fastembed"
    assert s.embed_cache_dir is None
    assert s.rerank_enabled is False
    assert s.rerank_model == "BAAI/bge-reranker-base"
    assert s.llm_monthly_budget_usd == 10.0
    assert s.llm_budget_alert_fraction == 0.8
    assert s.llm_prices[s.model_main] == ModelPrice(input=3.0, output=15.0)
    assert s.llm_prices[s.model_fast] == ModelPrice(input=1.0, output=5.0)
    assert s.llm_web_search_usd == 0.01
    assert s.data_dir == Path("data")
    assert s.device_token == ""
    assert s.upload_max_mb == 50
    assert s.upload_max_files == 20
    assert s.telegram_bot_token == ""
    assert s.telegram_poll_seconds == 2.0
    assert s.timezone == "UTC"


OVERRIDES = {
    "data_dir": ("/tmp/x", Path("/tmp/x")),
    "device_token": ("abc", "abc"),
    "upload_max_mb": ("5", 5),
    "upload_max_files": ("3", 3),
    "telegram_bot_token": ("123:fake", "123:fake"),
    "telegram_poll_seconds": ("0.5", 0.5),
    "timezone": ("Asia/Kolkata", "Asia/Kolkata"),
    "model_main": ("claude-sonnet-5-5", "claude-sonnet-5-5"),
    "model_fast": ("claude-haiku-4-5-20251001", "claude-haiku-4-5-20251001"),
    "anthropic_api_key": ("k1", "k1"),
    "llm_provider": ("anthropic", "anthropic"),
    "embed_model": ("e1", "e1"),
    "embed_provider": ("fake", "fake"),
    "embed_cache_dir": ("/tmp/models", Path("/tmp/models")),
    "rerank_enabled": ("true", True),
    "rerank_model": ("r1", "r1"),
    "rag_min_similarity": ("0.5", 0.5),
    "llm_monthly_budget_usd": ("25", 25.0),
    "llm_budget_alert_fraction": ("0.5", 0.5),
    "llm_prices": (
        '{"claude-sonnet-5-5":{"input":2,"output":4},"claude-haiku-4-5-20251001":{"input":1,"output":2}}',
        {
            "claude-sonnet-5-5": ModelPrice(input=2, output=4),
            "claude-haiku-4-5-20251001": ModelPrice(input=1, output=2),
        },
    ),
    "llm_web_search_usd": ("0.02", 0.02),
    "pin_length": ("6", 6),
    "pin_key": ("some-key", "some-key"),
    "pin_max_wrong": ("7", 7),
    "pin_lockout_seconds": ("600", 600),
    "pin_wrong_before_fallback": ("2", 2),
    "pin_resend_interval_seconds": ("30", 30),
    "fallback_max_wrong": ("4", 4),
    "fallback_lockout_seconds": ("1800", 1800),
    "inactivity_warn_seconds": ("120", 120),
    "inactivity_lock_seconds": ("600", 600),
    "grade_bands": (
        '{"A":95,"B":85,"C":70,"D":50,"F":0}',
        {"A": 95, "B": 85, "C": 70, "D": 50, "F": 0},
    ),
}


def test_overrides_cover_every_field() -> None:
    assert set(OVERRIDES) == set(Settings.model_fields)


@pytest.mark.parametrize("name", sorted(OVERRIDES))
def test_env_overrides(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    raw, expected = OVERRIDES[name]
    monkeypatch.setenv(name.upper(), raw)
    assert getattr(Settings(), name) == expected


def test_env_names_are_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("pin_length", "8")
    assert Settings().pin_length == 8


@pytest.mark.parametrize("raw", ["false", "0"])
def test_rerank_false_values(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("RERANK_ENABLED", raw)
    assert Settings().rerank_enabled is False


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "bands",
    [
        {"A": 90, "B": 50},
        {"A": 50, "B": 80, "F": 0},
        {"A": 90, "B": 90, "F": 0},
        {"A": 120, "F": 0},
        {"A": 90, "Z": 0},
        {},
    ],
)
def test_bad_grade_bands(bands: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        Settings(grade_bands=bands)


def test_invalid_grade_bands_json_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRADE_BANDS", "not json")
    with pytest.raises(ValueError):
        Settings()


def test_warn_must_precede_lock() -> None:
    with pytest.raises(ValidationError):
        Settings(inactivity_warn_seconds=300, inactivity_lock_seconds=240)


def test_fallback_reveal_not_after_lockout() -> None:
    with pytest.raises(ValidationError):
        Settings(pin_wrong_before_fallback=6, pin_max_wrong=5)


def test_pin_length_minimum() -> None:
    with pytest.raises(ValidationError):
        Settings(pin_length=3)


@pytest.mark.parametrize("fraction", [0, 1])
def test_alert_fraction_bounds(fraction: float) -> None:
    with pytest.raises(ValidationError):
        Settings(llm_budget_alert_fraction=fraction)


def test_model_without_price_fails() -> None:
    with pytest.raises(ValidationError):
        Settings(model_main="other-model")
    with pytest.raises(ValidationError):
        Settings(model_fast="other-model")


def test_model_with_price_passes() -> None:
    prices = {"other-model": ModelPrice(input=1, output=2)}
    s = Settings(model_main="other-model", model_fast="other-model", llm_prices=prices)
    assert s.llm_prices == prices


def test_negative_budget_fails() -> None:
    with pytest.raises(ValidationError):
        Settings(llm_monthly_budget_usd=-1)
