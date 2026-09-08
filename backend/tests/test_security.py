"""Password security contract tests."""

from app.security import hash_password, verify_password


def test_passwords_use_salted_argon2id_hashes() -> None:
    password = "correct horse battery staple"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash.startswith("$argon2id$")
    assert second_hash.startswith("$argon2id$")
    assert first_hash != second_hash
    assert verify_password(password, first_hash)
    assert not verify_password("different password", first_hash)


def test_password_unicode_is_normalized_consistently() -> None:
    composed = "Caf\u00e9 is a secure passphrase"
    decomposed = "Cafe\u0301 is a secure passphrase"

    encoded_hash = hash_password(composed)

    assert verify_password(decomposed, encoded_hash)
