"""Argon2id password primitives aligned with locked seed hashes."""
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from app.errors import ValidationError

hasher = PasswordHasher(memory_cost=19456, time_cost=2, parallelism=1)


def hash_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValidationError(details=[{'field': 'password', 'reason': 'Mật khẩu phải dài từ 12 đến 128 ký tự'}])
    return hasher.hash(password)


def verify_password(password_hash, password):
    if not isinstance(password_hash, str) or not password_hash.startswith('$argon2id$') or not isinstance(password, str) or not 12 <= len(password) <= 128:
        return False
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
