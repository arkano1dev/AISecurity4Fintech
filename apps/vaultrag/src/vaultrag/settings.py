from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class VaultragSettings(BaseSettings):
    """Typed configuration for VaultRAG.

    Every dependency URL and model name is configurable so the service can be
    pointed at the real shared services (pii-proxy, audit-log, Ollama) or at
    test doubles without code changes.
    """

    model_config = SettingsConfigDict(env_prefix="VAULTRAG_", extra="ignore")

    pii_proxy_url: str = "http://localhost:8002"
    audit_log_url: str = "http://localhost:8101"
    ollama_url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    llm_model: str = "deepseek-v4-pro:cloud"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4
    auth_service_url: str = "http://localhost:8000"
    audience: str = "agentflow"
    issuer: str = "auth"


settings = VaultragSettings()
