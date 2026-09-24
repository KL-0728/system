from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.auth import (
    SESSION_COOKIE,
    create_session,
    delete_session,
    get_current_user,
)
from backend.database import connect_database
from backend.schemas.auth import LoginRequest, MessageResponse, UserResponse
from backend.services.auth_service import AuthenticatedUser, authenticate


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response) -> AuthenticatedUser:
    with connect_database() as connection:
        user = authenticate(connection, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
        )
    token = create_session(user.id)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return user


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response) -> MessageResponse:
    delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="lax")
    return MessageResponse(message="已登出")


@router.get("/me", response_model=UserResponse)
def me(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    return user
