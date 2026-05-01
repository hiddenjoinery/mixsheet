"""Runtime settings loaded from environment and ``.env``."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Top-level runtime settings.

    Configuration values are loaded with this precedence (highest first):
    constructor arguments, environment variables, ``.env`` file values,
    declared defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MIXSHEET_",
        extra="ignore",
    )

    app_name: str = "The Mix Sheet"
    config_dir: Path = REPO_ROOT / "config"

    pydantic_config = ConfigDict(strict=True)


def get_settings() -> Settings:
    """Return a fresh ``Settings`` instance.

    A function (not a module-level constant) keeps tests free to override
    environment variables before construction.
    """
    return Settings()
