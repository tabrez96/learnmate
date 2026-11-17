"""Server settings and the adjustable product defaults, all overridable from the environment."""

import itertools
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    # Deployment
    data_dir: Path = Path("data")
    device_token: str = ""

    # Uploads
    upload_max_mb: int = 50
    upload_max_files: int = 20

    # Telegram
    telegram_bot_token: str = ""
    telegram_poll_seconds: float = 2.0
    # IANA name; times in messages are shown in this zone.
    timezone: str = "UTC"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'learnmate.db'}"

    # AI
    model_main: str = "claude-sonnet-5-5"
    model_fast: str = "claude-haiku-4-5-20251001"
    anthropic_api_key: str = ""
    llm_provider: Literal["anthropic", "fake"] = "anthropic"
    embed_model: str = "BAAI/bge-small-en-v1.5"
    rerank_enabled: bool = False
    llm_monthly_budget_usd: float = 10.0
    llm_budget_alert_fraction: float = 0.8

    # Session PIN
    pin_length: int = 4
    pin_max_wrong: int = 5
    pin_lockout_seconds: int = 15 * 60
    pin_wrong_before_fallback: int = 3
    pin_resend_interval_seconds: int = 60

    # Fallback password
    fallback_max_wrong: int = 3
    fallback_lockout_seconds: int = 60 * 60

    # Inactivity
    inactivity_warn_seconds: int = 240
    inactivity_lock_seconds: int = 300

    # Grade bands: lowest percentage for each band, highest band first.
    grade_bands: dict[str, int] = {"A": 90, "B": 80, "C": 70, "D": 60, "F": 0}

    @field_validator("grade_bands")
    @classmethod
    def _check_grade_bands(cls, bands: dict[str, int]) -> dict[str, int]:
        if not bands:
            raise ValueError("grade_bands must not be empty")
        values = list(bands.values())
        if any(not 0 <= v <= 100 for v in values):
            raise ValueError("grade_bands values must be between 0 and 100")
        if any(a <= b for a, b in itertools.pairwise(values)):
            raise ValueError("grade_bands values must strictly descend")
        if values[-1] != 0:
            raise ValueError("the lowest grade band must start at 0")
        return bands

    @model_validator(mode="after")
    def _check_relations(self) -> Settings:
        if self.inactivity_warn_seconds >= self.inactivity_lock_seconds:
            raise ValueError(
                "inactivity_warn_seconds must be below inactivity_lock_seconds"
            )
        if self.pin_wrong_before_fallback > self.pin_max_wrong:
            raise ValueError("pin_wrong_before_fallback must not exceed pin_max_wrong")
        if self.pin_length < 4:
            raise ValueError("pin_length must be at least 4")
        if not 0 < self.llm_budget_alert_fraction < 1:
            raise ValueError("llm_budget_alert_fraction must be between 0 and 1")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
