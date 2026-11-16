from learnmate.passwords import hash_password, verify_password


def test_hash_is_argon2id() -> None:
    hashed = hash_password("correct horse")
    assert hashed.startswith("$argon2id$")
    assert "correct horse" not in hashed


def test_verify_accepts_right_and_rejects_wrong() -> None:
    hashed = hash_password("correct horse")
    assert verify_password("correct horse", hashed) is True
    assert verify_password("battery staple", hashed) is False


def test_verify_handles_none_and_garbage() -> None:
    assert verify_password("x", None) is False
    assert verify_password("x", "not-a-hash") is False
