import time
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from config.settings import JWT_SECRET, PORTAL_PASSWORD, PORTAL_USERNAME

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)

_TOKEN_TTL = 7 * 24 * 3600  # 7 days


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    if body.username != PORTAL_USERNAME or body.password != PORTAL_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    now = int(time.time())
    token = jwt.encode(
        {"sub": body.username, "iat": now, "exp": now + _TOKEN_TTL},
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"token": token}


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
