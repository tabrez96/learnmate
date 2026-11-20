import stat
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from learnmate.config import Settings
from learnmate.models import StudySession
from learnmate.sessions import pins
from learnmate.sessions.pins import (
    generate_pin,
    load_pin_cipher,
    read_pin,
    set_pin,
    verify_pin,
)


def _row() -> StudySession:
    return StudySession(type="learn", question_count=5)


def test_generate_pin_is_digits_of_length() -> None:
    for _ in range(200):
        pin = generate_pin(4)
        assert len(pin) == 4 and pin.isdigit()
    assert len(generate_pin(6)) == 6


def test_generate_pin_avoids_old(monkeypatch: pytest.MonkeyPatch) -> None:
    draws = iter([1234, 1234, 5678])
    monkeypatch.setattr(pins.secrets, "randbelow", lambda _n: next(draws))
    assert generate_pin(4, avoid="1234") == "5678"


def test_set_pin_hashes_and_encrypts() -> None:
    cipher = Fernet(Fernet.generate_key())
    row = _row()
    set_pin(row, "1234", cipher)
    assert "1234" not in row.pin_hash
    assert "1234" not in row.pin_enc
    assert verify_pin(row, "1234")
    assert read_pin(row, cipher) == "1234"


def test_read_pin_none_without_copy_or_with_wrong_key() -> None:
    row = _row()
    assert read_pin(row, Fernet(Fernet.generate_key())) is None
    set_pin(row, "1234", Fernet(Fernet.generate_key()))
    assert read_pin(row, Fernet(Fernet.generate_key())) is None


def test_verify_pin_rejects_wrong_and_missing() -> None:
    row = _row()
    set_pin(row, "1234", Fernet(Fernet.generate_key()))
    assert verify_pin(row, "4321") is False
    row.pin_hash = None
    assert verify_pin(row, "1234") is False


def test_load_pin_cipher_creates_key_file_once(settings: Settings) -> None:
    first = load_pin_cipher(settings)
    path = settings.data_dir / pins.KEY_FILE
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    second = load_pin_cipher(settings)
    assert second.decrypt(first.encrypt(b"1234")) == b"1234"


def test_load_pin_cipher_uses_setting(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        pin_key=Fernet.generate_key().decode(),
        llm_provider="fake",
        embed_provider="fake",
    )
    load_pin_cipher(settings)
    assert not (settings.data_dir / pins.KEY_FILE).exists()


def test_load_pin_cipher_rejects_bad_key(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, pin_key="nope")
    with pytest.raises(ValueError):
        load_pin_cipher(settings)
