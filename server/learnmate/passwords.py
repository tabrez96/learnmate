"""Argon2id hashing for the fallback password."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # argon2-cffi defaults are argon2id


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    """False for no hash, a mismatch or a malformed hash; never raises."""
    if hashed is None:
        return False
    try:
        return _hasher.verify(hashed, password)
    except VerificationError, InvalidHashError:
        return False
