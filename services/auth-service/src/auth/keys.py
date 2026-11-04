from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from auth.config import settings

KEY_DIR = Path(__file__).resolve().parents[2] / ".keys"
KEY_DIR.mkdir(parents=True, exist_ok=True)
REGISTRY_DIR = KEY_DIR / "registry"
ACTIVE_KID_PATH = KEY_DIR / "active.kid"
_key_registry: dict[str, KeyHandle] = {}
_active_key_id: str | None = None


class KeyHandle:
    def __init__(self, private_key: rsa.RSAPrivateKey, key_id: str | None = None):
        self._private_key = private_key
        self.key_id = key_id or str(uuid.uuid4())

    @property
    def private_key(self) -> rsa.RSAPrivateKey:
        return self._private_key

    def public_key(self) -> rsa.RSAPublicKey:
        return self._private_key.public_key()


def _write_private_key(key: rsa.RSAPrivateKey) -> None:
    settings.auth_private_key_path.parent.mkdir(parents=True, exist_ok=True)
    settings.auth_private_key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(settings.auth_private_key_path, 0o600)


def _write_public_key(key: rsa.RSAPublicKey) -> None:
    settings.auth_public_key_path.parent.mkdir(parents=True, exist_ok=True)
    settings.auth_public_key_path.write_bytes(
        key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def generate_rsa_keypair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    _write_private_key(private_key)
    _write_public_key(public_key)
    return private_key, public_key


def load_private_key() -> KeyHandle:
    global _active_key_id

    if not settings.auth_private_key_path.exists():
        generate_rsa_keypair()
    key_bytes = settings.auth_private_key_path.read_bytes()
    private_key = serialization.load_pem_private_key(key_bytes, password=None)
    kid_path = settings.auth_private_key_path.with_suffix(".kid")
    if not kid_path.exists():
        kid_path.write_text(str(uuid.uuid4()), encoding="ascii")
    key_id = kid_path.read_text(encoding="ascii").strip()
    return KeyHandle(private_key, key_id=key_id)


def get_active_private_key() -> KeyHandle:
    global _active_key_id

    if _active_key_id in _key_registry:
        return _key_registry[_active_key_id]

    base_key = load_private_key()
    _key_registry.setdefault(base_key.key_id, base_key)
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    for private_key_path in REGISTRY_DIR.glob("*.pem"):
        private_key = serialization.load_pem_private_key(
            private_key_path.read_bytes(), password=None
        )
        _key_registry.setdefault(
            private_key_path.stem,
            KeyHandle(private_key, key_id=private_key_path.stem),
        )

    if _active_key_id is None and ACTIVE_KID_PATH.exists():
        _active_key_id = ACTIVE_KID_PATH.read_text(encoding="ascii").strip()
    if _active_key_id not in _key_registry:
        _active_key_id = base_key.key_id
    ACTIVE_KID_PATH.write_text(_active_key_id, encoding="ascii")
    return _key_registry[_active_key_id]


def register_key(key_handle: KeyHandle, active: bool = False) -> None:
    global _active_key_id

    _key_registry[key_handle.key_id] = key_handle
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    private_key_path = REGISTRY_DIR / f"{key_handle.key_id}.pem"
    private_key_path.write_bytes(
        key_handle.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(private_key_path, 0o600)
    if active or _active_key_id is None:
        _active_key_id = key_handle.key_id
        ACTIVE_KID_PATH.write_text(_active_key_id, encoding="ascii")


def get_registered_key(key_id: str) -> KeyHandle | None:
    if not _key_registry or key_id not in _key_registry:
        get_active_private_key()
    return _key_registry.get(key_id)


def jwk_from_public_key(public_key: rsa.RSAPublicKey, kid: str | None = None) -> dict[str, str]:
    public_numbers = public_key.public_numbers()
    n = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, byteorder="big")
    e = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, byteorder="big")
    return {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": kid or str(uuid.uuid4()),
        "n": _b64url_encode(n),
        "e": _b64url_encode(e),
    }


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def get_public_jwk_set() -> dict[str, list[dict[str, str]]]:
    get_active_private_key()
    return {
        "keys": [
            jwk_from_public_key(key.public_key(), kid=key_id)
            for key_id, key in _key_registry.items()
        ]
    }
