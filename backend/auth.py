import hashlib
import os
import secrets

_ITERATIONS = 200_000


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    ).hex()


def create_user_password(password: str):
    salt = secrets.token_hex(16)
    return salt, hash_password(password, salt)


def verify_password(password: str, salt: str, expected: str) -> bool:
    return secrets.compare_digest(hash_password(password, salt), expected)


def new_token() -> str:
    return secrets.token_urlsafe(48)
