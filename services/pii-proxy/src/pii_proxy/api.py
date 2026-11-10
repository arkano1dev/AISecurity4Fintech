import re
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from pii_proxy.auth import TokenVerifier, require_auth
from pii_proxy.models import MaskRequest, MaskResponse, VaultRequest, VaultResponse
from pii_proxy.vault import SecretVault

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
PAN_RE = re.compile(r"\b\d{4}(?:[\s-]?\d{4}){3}\b")
PHONE_RE = re.compile(r"\+?\d{1,3}[\s.-]?\d{3}[\s.-]?\d{3}[\s.-]?\d{4}")


def redact_text(text: str) -> str:
    redacted = text
    for pattern, label in (
        (EMAIL_RE, "[EMAIL]"),
        (IBAN_RE, "[IBAN]"),
        (PAN_RE, "[PAN]"),
        (PHONE_RE, "[PHONE]"),
        (SSN_RE, "[SSN]"),
        (DATE_RE, "[DATE]"),
    ):
        redacted = pattern.sub(label, redacted)
    return redacted


def make_app(*, verify_token_fn: TokenVerifier | None = None) -> FastAPI:
    app = FastAPI(title="PII Proxy")
    app.state.vault = SecretVault()

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/pii/mask", response_model=MaskResponse)
    def mask(payload: MaskRequest) -> MaskResponse:
        return MaskResponse(redacted=redact_text(payload.text))

    @app.post("/pii/vault", response_model=VaultResponse, status_code=201)
    def store(
        payload: VaultRequest,
        _auth: Annotated[
            dict[str, Any],
            Depends(require_auth(["pii:store"], verify_token_fn)),
        ],
    ) -> VaultResponse:
        receipt = app.state.vault.store(payload.record_type, payload.payload)
        return VaultResponse(receipt=receipt, message="stored")

    @app.get("/pii/receipt/{receipt}", response_model=None)
    def fetch_receipt(
        receipt: str,
        _auth: Annotated[
            dict[str, Any],
            Depends(require_auth(["pii:read"], verify_token_fn)),
        ],
    ) -> dict[str, object] | JSONResponse:
        record = app.state.vault.get(receipt)
        if record is None:
            return JSONResponse(status_code=404, content={"detail": "receipt not found"})
        return {"receipt": receipt, "record": record}

    return app
