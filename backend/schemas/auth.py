from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str


class MessageResponse(BaseModel):
    message: str
