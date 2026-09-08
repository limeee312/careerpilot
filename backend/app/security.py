"""Password hashing primitives shared by authentication flows."""

import unicodedata

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def normalize_password(password: str) -> str:
    """Normalize Unicode without trimming or changing intentional whitespace."""

    return unicodedata.normalize("NFC", password)


def hash_password(password: str) -> str:
    """Hash a password using pwdlib's recommended Argon2id configuration."""

    return password_hash.hash(normalize_password(password))


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password against a stored hash."""

    return password_hash.verify(normalize_password(password), encoded_hash)
