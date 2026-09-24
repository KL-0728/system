import secrets
from collections.abc import Callable

from fastapi import Cookie, Depends, HTTPException, status

from backend.database import connect_database
from backend.services.auth_service import AuthenticatedUser, find_active_user


SESSION_COOKIE = "inventory_session"
_sessions: dict[str, int] = {}


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = user_id
    return token


def delete_session(token: str | None) -> None:
    if token:
        _sessions.pop(token, None)


def get_current_user(
    inventory_session: str | None = Cookie(default=None),
) -> AuthenticatedUser:
    user_id = _sessions.get(inventory_session or "")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="請先登入"
        )
    with connect_database() as connection:
        user = find_active_user(connection, user_id)
    if user is None:
        delete_session(inventory_session)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="登入已失效"
        )
    return user


def require_roles(*roles: str) -> Callable[..., AuthenticatedUser]:
    def dependency(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="權限不足"
            )
        return user

    return dependency


require_admin = require_roles("ADMIN")
require_worker = require_roles("WORKER")
