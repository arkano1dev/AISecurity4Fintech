from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from auth.keys import get_active_private_key
from auth.jwt import issue_token, verify_token


def test_issue_token_has_required_claims() -> None:
    token = issue_token({"username": "alice"}, ["agentflow"], ["chat:send", "account:read"])
    payload = jwt.decode(token, options={"verify_signature": False})

    assert payload["sub"] == "alice"
    assert payload["iss"] == "auth"
    assert payload["aud"] == "agentflow"
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()
    assert payload["jti"]
    assert payload["scopes"] == ["chat:send", "account:read"]


def test_issue_token_uses_rs256_alg_header() -> None:
    token = issue_token({"username": "alice"}, ["agentflow"], ["chat:send"])
    assert jwt.get_unverified_header(token)["alg"] == "RS256"


def test_verify_rejects_hs256_alg() -> None:
    key = "super-secret-key"
    token = jwt.encode(
        {"sub": "alice", "scopes": ["chat:send"], "iss": "auth", "aud": "agentflow", "exp": 9999999999, "jti": "hs256-1"},
        key,
        algorithm="HS256",
    )
    result = verify_token(token, "agentflow")
    assert result.valid is False
    assert result.reason == "invalid_algorithm"


def test_verify_rejects_none_alg() -> None:
    token = jwt.encode(
        {"sub": "alice", "scopes": ["chat:send"], "iss": "auth", "aud": "agentflow", "exp": 9999999999, "jti": "none-1"},
        key=None,
        algorithm="none",
    )
    result = verify_token(token, "agentflow")
    assert result.valid is False
    assert result.reason == "invalid_algorithm"


def test_kid_header_matches_signing_key() -> None:
    private_key = get_active_private_key()
    token = issue_token({"username": "alice"}, ["agentflow"], ["chat:send"])
    header = jwt.get_unverified_header(token)
    assert header["kid"] == private_key.key_id


def test_scope_present_in_issue() -> None:
    token = issue_token({"username": "alice"}, ["agentflow"], ["a", "b"])
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["scopes"] == ["a", "b"]
    assert payload["scope"] == "a b"
