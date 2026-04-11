import time

import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from config.settings import JWT_SECRET, PORTAL_PASSWORD, PORTAL_USERNAME

router = APIRouter(prefix="/auth", tags=["auth"])

_TOKEN_TTL = 7 * 24 * 3600  # 7 days
_COOKIE_NAME = "ops_auth_token"

# NOTE: JWT logic is mirrored in user_portal/backend/api/auth.py.
# If you change the algorithm, TTL, or token structure, update both files.


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    if body.username != PORTAL_USERNAME or body.password != PORTAL_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    now = int(time.time())
    token = jwt.encode(
        {"sub": body.username, "iat": now, "exp": now + _TOKEN_TTL},
        JWT_SECRET,
        algorithm="HS256",
    )
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        max_age=_TOKEN_TTL,
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=_COOKIE_NAME, samesite="strict")
    return {"ok": True}


def verify_token(request: Request):
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
