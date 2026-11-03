from __future__ import annotations

import base64
import uuid
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from auth.config import settings


KEY_DIR = Path(__file__).resolve().parents[2] / ".keys"
KEY_DIR.mkdir(parents=True, exist_ok=True)


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
    if not settings.auth_private_key_path.exists():
        generate_rsa_keypair()
    key_bytes = settings.auth_private_key_path.read_bytes()
    private_key = serialization.load_pem_private_key(key_bytes, password=None)
    return KeyHandle(private_key, key_id="active")


def get_active_private_key() -> KeyHandle:
    return load_private_key()


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
    public_key = get_active_private_key().public_key()
    return {"keys": [jwk_from_public_key(public_key, kid=get_active_private_key().key_id)]}
