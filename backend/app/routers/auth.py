from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from pymongo.errors import DuplicateKeyError

from ..config import settings
from ..db import db
from ..deps import get_current_user
from ..security import (create_access_token, hash_password, hash_token,
                        new_refresh_token, verify_password)
from ..utils import utcnow

router = APIRouter(prefix="/api/auth", tags=["auth"])
COOKIE = "refresh_token"


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    remember_me: bool = True


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


def user_out(u) -> dict:
    return {"id": str(u["_id"]), "name": u["name"], "email": u["email"]}


async def start_session(response: Response, user: dict, remember: bool) -> dict:
    """Create a refresh token (server-side hashed, httpOnly cookie) + short-lived access JWT."""
    days = settings.refresh_days_remember if remember else settings.refresh_days_session
    raw = new_refresh_token()
    await db.refresh_tokens.insert_one({
        "token_hash": hash_token(raw), "user_id": user["_id"], "remember": remember,
        "created_at": utcnow(), "expires_at": utcnow() + timedelta(days=days),
    })
    response.set_cookie(
        COOKIE, raw, httponly=True, secure=settings.cookie_secure, samesite="lax",
        path="/api/auth",
        max_age=days * 86400 if remember else None,  # None -> dies when the browser closes
    )
    return {"access_token": create_access_token(str(user["_id"])),
            "token_type": "bearer", "user": user_out(user)}


@router.post("/register", status_code=201)
async def register(body: RegisterIn, response: Response):
    user = {"name": body.name.strip(), "email": body.email.lower(),
            "password_hash": hash_password(body.password), "created_at": utcnow()}
    try:
        res = await db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(409, "An account with this email already exists")
    user["_id"] = res.inserted_id
    return await start_session(response, user, body.remember_me)


@router.post("/login")
async def login(body: LoginIn, response: Response):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    return await start_session(response, user, body.remember_me)


@router.post("/refresh")
async def refresh(response: Response, refresh_token: str | None = Cookie(default=None)):
    """Rotate the refresh token and hand out a new access token."""
    if not refresh_token:
        raise HTTPException(401, "No session")
    doc = await db.refresh_tokens.find_one_and_delete({"token_hash": hash_token(refresh_token)})
    if not doc or doc["expires_at"] < utcnow():
        response.delete_cookie(COOKIE, path="/api/auth")
        raise HTTPException(401, "Session expired")
    user = await db.users.find_one({"_id": doc["user_id"]})
    if not user:
        raise HTTPException(401, "User no longer exists")
    return await start_session(response, user, doc["remember"])


@router.post("/logout", status_code=204)
async def logout(response: Response, refresh_token: str | None = Cookie(default=None)):
    if refresh_token:
        await db.refresh_tokens.delete_one({"token_hash": hash_token(refresh_token)})
    response.delete_cookie(COOKIE, path="/api/auth")


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user_out(user)
