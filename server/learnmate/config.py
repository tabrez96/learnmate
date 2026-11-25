"""Server settings and the adjustable product defaults, all overridable from the environment."""

import itertools
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from learnmate.models import GRADE_BANDS


class ModelPrice(BaseModel):
    """USD per million tokens."""

    input: float = Field(ge=0)
    output: float = Field(ge=0)


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
    def database_path(self) -> Path:
        return self.data_dir / "learnmate.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    # AI
    model_main: str = "claude-sonnet-5-5"
    model_fast: str = "claude-haiku-4-5-20251001"
    anthropic_api_key: str = ""
    llm_provider: Literal["anthropic", "fake"] = "anthropic"
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_provider: Literal["fastembed", "fake"] = "fastembed"
    # Where fastembed keeps downloaded model files; None uses fastembed's default.
    embed_cache_dir: Path | None = None
    # Off by the retrieval eval (docs/retrieval-eval.md): committed-set recall@6 is 1.000
    # without and with it (MRR 0.950 -> 0.983, 0.30 s per question).
    # test_rerank_default_matches_eval fails if the reranker improves recall@6 within
    # 1.5 s per question while this is off.
    rerank_enabled: bool = False
    # Cross-encoder that rescores the fused top 20 when RERANK_ENABLED is on.
    rerank_model: str = "BAAI/bge-reranker-base"
    # Relevance floor: a search with no keyword match returns nothing when the best
    # cosine is below this. Tuned with tests/rag (docs/retrieval-eval.md) for
    # bge-small-en-v1.5; re-tune with the eval when EMBED_MODEL changes.
    # Chosen 0.53: committed set off-topic max 0.499, floor-dependent min 0.555 (tests/rag).
    rag_min_similarity: float = Field(0.53, ge=0, le=1)
    llm_monthly_budget_usd: float = 10.0
    llm_budget_alert_fraction: float = 0.8
    # USD per million tokens for each model; override as JSON, e.g.
    # LLM_PRICES='{"<model id>": {"input": 3, "output": 15}}'.
    llm_prices: dict[str, ModelPrice] = {
        "claude-sonnet-5-5": ModelPrice(input=3.0, output=15.0),
        "claude-haiku-4-5-20251001": ModelPrice(input=1.0, output=5.0),
    }
    llm_web_search_usd: float = Field(0.01, ge=0)  # per search

    # Session PIN
    pin_length: int = 4
    # Fernet key for the encrypted PIN copy; empty means a key file in data_dir.
    pin_key: str = ""
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

    # Presence: the watchdog treats a running session with no heartbeat for this long as "left".
    heartbeat_timeout_seconds: int = 45
    watchdog_interval_seconds: float = 10.0
    # Off in tests, which run one watchdog pass at a time with a fake clock.
    watchdog_enabled: bool = True

    # Backups: nightly at BACKUP_HOUR (local time in TIMEZONE) into BACKUP_DIR, kept BACKUP_KEEP_DAYS days.
    backup_dir: Path = Path("backups")
    backup_hour: int = 3
    backup_keep_days: int = 14
    # Off in tests, which call run_backup directly with a fake clock.
    backup_enabled: bool = True

    # Grade bands: lowest percentage for each band, highest band first.
    grade_bands: dict[str, int] = {"A": 90, "B": 80, "C": 70, "D": 60, "E": 50, "F": 0}

    @field_validator("grade_bands")
    @classmethod
    def _check_grade_bands(cls, bands: dict[str, int]) -> dict[str, int]:
        if not bands:
            raise ValueError("grade_bands must not be empty")
        if any(band not in GRADE_BANDS for band in bands):
            raise ValueError(f"grade_bands keys must be among {', '.join(GRADE_BANDS)}")
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
        if self.pin_max_wrong < 1:
            raise ValueError("pin_max_wrong must be at least 1")
        if not 4 <= self.pin_length <= 12:
            raise ValueError("pin_length must be between 4 and 12")
        if not 0 < self.llm_budget_alert_fraction < 1:
            raise ValueError("llm_budget_alert_fraction must be between 0 and 1")
        for model in (self.model_main, self.model_fast):
            if model not in self.llm_prices:
                raise ValueError(f"llm_prices has no price for {model}")
        if self.llm_monthly_budget_usd < 0:
            raise ValueError("llm_monthly_budget_usd must not be negative")
        if not 0 <= self.backup_hour <= 23:
            raise ValueError("backup_hour must be between 0 and 23")
        if self.backup_keep_days < 1:
            raise ValueError("backup_keep_days must be at least 1")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
