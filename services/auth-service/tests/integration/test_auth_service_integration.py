from __future__ import annotations

from pathlib import Path

import jwt
import pytest
from auth import keys
from auth.api import make_app
from auth.jwt import issue_token, verify_token
from auth.keys import KeyHandle, get_active_private_key, get_public_jwk_set, register_key
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient


def test_full_flow_issue_then_verify_against_real_keypair() -> None:
    client = TestClient(make_app())
    issued = client.post("/auth/token", json={"username": "alice", "password": "correct-horse"})
    assert issued.status_code == 200
    result = client.post("/auth/verify", json={"token": issued.json()["access_token"]})
    assert result.status_code == 200
    assert result.json()["valid"] is True
    assert result.json()["sub"] == "alice"


def test_jwks_matches_signing_key_by_kid() -> None:
    token = issue_token({"username": "alice"}, ["agentflow"], ["chat:send"])
    kid = jwt.get_unverified_header(token)["kid"]
    keys_by_kid = {jwk["kid"]: jwk for jwk in get_public_jwk_set()["keys"]}
    assert kid in keys_by_kid
    assert keys_by_kid[kid]["n"]
    assert keys_by_kid[kid]["e"] == "AQAB"


def test_rotation_adds_new_kid_and_old_still_verifies_in_grace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(keys, "KEY_DIR", tmp_path)
    monkeypatch.setattr(keys, "REGISTRY_DIR", tmp_path / "registry")
    monkeypatch.setattr(keys, "ACTIVE_KID_PATH", tmp_path / "active.kid")
    monkeypatch.setattr(keys, "_key_registry", {}, raising=False)
    monkeypatch.setattr(keys, "_active_key_id", None, raising=False)
    old_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    old_key = KeyHandle(old_private, key_id="k1")
    register_key(old_key, active=True)
    old_token = issue_token({"username": "alice"}, ["agentflow"], ["chat:send"])

    new_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    register_key(KeyHandle(new_private, key_id="k2"), active=True)

    result = verify_token(old_token, "agentflow")
    assert result.valid is True
    assert result.sub == "alice"
    assert {jwk["kid"] for jwk in get_public_jwk_set()["keys"]} == {"k1", "k2"}

    monkeypatch.setattr(keys, "_key_registry", {}, raising=False)
    monkeypatch.setattr(keys, "_active_key_id", None, raising=False)
    assert get_active_private_key().key_id == "k2"
    assert verify_token(old_token, "agentflow").valid is True
