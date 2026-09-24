import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass


PBKDF2_ITERATIONS = 600_000


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    username: str
    display_name: str
    role: str


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(actual, bytes.fromhex(expected_hex))
    except (ValueError, TypeError):
        return False


def authenticate(
    connection: sqlite3.Connection, username: str, password: str
) -> AuthenticatedUser | None:
    row = connection.execute(
        """
        SELECT id, username, password_hash, display_name, role
        FROM users
        WHERE username = ? AND is_active = 1
        """,
        (username.strip(),),
    ).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        return None
    return AuthenticatedUser(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        role=row["role"],
    )


def find_active_user(
    connection: sqlite3.Connection, user_id: int
) -> AuthenticatedUser | None:
    row = connection.execute(
        """
        SELECT id, username, display_name, role
        FROM users
        WHERE id = ? AND is_active = 1
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return AuthenticatedUser(**dict(row))
