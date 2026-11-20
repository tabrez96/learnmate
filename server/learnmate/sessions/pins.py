"""Session PINs: random digits, an Argon2 hash to check them and a Fernet copy to resend them."""

import os
import secrets

from cryptography.fernet import Fernet, InvalidToken

from learnmate.config import Settings
from learnmate.models import StudySession
from learnmate.passwords import hash_password, verify_password

KEY_FILE = "pin.key"


def load_pin_cipher(settings: Settings) -> Fernet:
    """Fernet from PIN_KEY, else from data_dir/pin.key (created on first use).

    A malformed key raises ValueError, so a bad PIN_KEY fails at start-up.
    """
    if settings.pin_key:
        return Fernet(settings.pin_key)
    path = settings.data_dir / KEY_FILE
    if not path.exists():
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as key_file:
            key_file.write(Fernet.generate_key())
    return Fernet(path.read_bytes().strip())


def generate_pin(length: int, *, avoid: str | None = None) -> str:
    while True:
        pin = f"{secrets.randbelow(10**length):0{length}d}"
        if pin != avoid:
            return pin


def set_pin(row: StudySession, pin: str, cipher: Fernet) -> None:
    row.pin_hash = hash_password(pin)
    row.pin_enc = cipher.encrypt(pin.encode()).decode()


def read_pin(row: StudySession, cipher: Fernet) -> str | None:
    """The stored PIN, or None when there is none or the key doesn't fit."""
    if row.pin_enc is None:
        return None
    try:
        return cipher.decrypt(row.pin_enc.encode()).decode()
    except InvalidToken:
        return None


def verify_pin(row: StudySession, pin: str) -> bool:
    return verify_password(pin, row.pin_hash)
