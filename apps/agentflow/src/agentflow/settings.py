from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentflowSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTFLOW_", extra="ignore")

    auth_service_url: str = "http://localhost:8000"
    auth_service_jwks_ttl_seconds: int = 300
    token_ttl_seconds: int = 900
    audience: str = "agentflow"
    issuer: str = "auth"
    audit_log_url: str = "http://localhost:8101"
    vaultrag_url: str = "http://localhost:8003"
    pii_proxy_url: str = "http://localhost:8002"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "deepseek-v4-pro:cloud"


settings = AgentflowSettings()
