# app/core/security.py
# Job of this file: hash/check passwords (bcrypt) and create/read login tokens (JWT).

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def _to_bytes(password: str) -> bytes:
    """bcrypt only looks at the first 72 BYTES of a password, and newer bcrypt
    versions raise an error if it is longer. We cut to 72 bytes on purpose,
    the same way in hashing and checking, so both always agree."""
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    """Turn a password into a scrambled hash we can safely store.
    gensalt() adds a random salt, so equal passwords get different hashes."""
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """True if the typed password matches the stored hash, else False."""
    try:
        return bcrypt.checkpw(_to_bytes(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        # A broken/invalid hash must count as "wrong password", not crash the app.
        return False


def create_access_token(user_id: int) -> str:
    """Make a signed JWT for this user.
    sub = who the token is for (JWT rules say it must be a string).
    iat = issued at, exp = expiry time. We do NOT put the role inside: the
    role is read fresh from the database on each request, so it can't be stale."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Check the signature and expiry. Returns the payload, or None if the token
    is fake, tampered with or expired. We name the allowed algorithm explicitly,
    so an attacker cannot trick us into accepting a different (weaker) one."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None