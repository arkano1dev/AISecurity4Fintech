from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MaskRequest(BaseModel):
    text: str = Field(..., min_length=1)


class MaskResponse(BaseModel):
    redacted: str


class VaultRequest(BaseModel):
    record_type: str = Field(..., min_length=1)
    payload: dict[str, Any]


class VaultResponse(BaseModel):
    receipt: str
    message: str = "stored"
