from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Register(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=100)


class Login(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class Refresh(BaseModel):
    refresh_token: str


class ProfilePatch(BaseModel):
    display_name: str = Field(max_length=100)


class Profile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    display_name: str
    role: str


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900
