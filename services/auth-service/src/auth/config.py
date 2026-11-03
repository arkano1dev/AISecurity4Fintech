from __future__ import annotations

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    auth_private_key_path: Path = Path(__file__).resolve().parents[2] / ".keys" / "auth_private.pem"
    auth_public_key_path: Path = Path(__file__).resolve().parents[2] / ".keys" / "auth_public.pem"
    auth_audiences: list[str] = ["agentflow"]
    auth_token_ttl: int = 900
    auth_issuer: str = "auth"
    auth_jwks_ttl: int = 300
    auth_user_file: Path = Path(__file__).resolve().parents[2] / "config" / "users.yaml"


settings = AuthSettings()


def load_users() -> dict[str, dict[str, object]]:
    if not settings.auth_user_file.exists():
        return {}
    data = yaml.safe_load(settings.auth_user_file.read_text(encoding="utf-8")) or {}
    return data.get("users", {})
