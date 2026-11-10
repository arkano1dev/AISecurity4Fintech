from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class PiiProxySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PII_PROXY_", extra="ignore")

    auth_service_url: str = "http://localhost:8000"
    audience: str = "agentflow"
    issuer: str = "auth"


settings = PiiProxySettings()
