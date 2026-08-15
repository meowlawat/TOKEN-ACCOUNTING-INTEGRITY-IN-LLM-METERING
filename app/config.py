"""Central configuration and the VULNERABLE <-> HARDENED posture toggles.

Every flaw class in the taxonomy is exposed here as a `Mode` toggle so the same
gateway binary can be run either vulnerable-by-construction or hardened. The
current process posture starts from these defaults and can be flipped at runtime
per class via `POST /admin/config` (see `app.main`), which is what the experiment
runners use to A/B a single class without restarting the container.
"""

from __future__ import annotations

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Mode(str, Enum):
    """Posture of a single flaw class."""

    vulnerable = "vulnerable"
    hardened = "hardened"


class Settings(BaseSettings):
    """Process-wide settings, overridable via environment / `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Infrastructure -----------------------------------------------------
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/metering"
    redis_url: str = "redis://localhost:6379/0"

    # --- Flaw-class posture (default at process start) ----------------------
    # 1..5 are the novel contribution; 6 is the known baseline used to validate
    # the measurement rig. Only class 6 is implemented in Phase 0.
    class6_credit_race: Mode = Mode.vulnerable

    # --- Mock pricing (mock dollars per 1k tokens) --------------------------
    # Values are chosen so a single request's cost is exactly representable in
    # NUMERIC(18,6); this keeps `balance = k * cost` exact for clean attack math.
    price_prompt_per_1k: float = 0.5
    price_completion_per_1k: float = 1.5

    # --- Deterministic mock model ------------------------------------------
    seed: int = 1337
    mock_min_tokens: int = 40
    mock_max_tokens: int = 80
    mock_inter_token_delay_ms: float = 5.0

    # --- DB pool sizing (needs to exceed experiment concurrency) ------------
    db_pool_size: int = 50
    db_max_overflow: int = 50


settings = Settings()
