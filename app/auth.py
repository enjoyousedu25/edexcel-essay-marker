from __future__ import annotations
import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response
from typing import Optional, List

COOKIE_NAME = "eem_session"
MAX_AGE_SECONDS = 60 * 60 * 10  # 10 hours

def _get_secret() -> str:
    # Render provides a service-wide secret key; otherwise fallback
    return os.getenv("SECRET_KEY", "dev-secret-change-me")

def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_get_secret(), salt="eem-auth")

def _valid_passcodes() -> List[str]:
    many = os.getenv("APP_PASSCODES", "").strip()
    if many:
        return [p.strip() for p in many.split(",") if p.strip()]
    one = os.getenv("APP_PASSCODE", "").strip()
    return [one] if one else []

def is_configured() -> bool:
    return len(_valid_passcodes()) > 0

def verify_passcode(passcode: str) -> bool:
    passcode = (passcode or "").strip()
    return passcode in _valid_passcodes()

def login(response: Response, teacher_name: str = "Teacher") -> None:
    token = _serializer().dumps({"teacher": teacher_name})
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=MAX_AGE_SECONDS,
        httponly=True,
        secure=True,  # Render uses HTTPS
        samesite="lax",
    )

def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)

def current_teacher(request: Request) -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=MAX_AGE_SECONDS)
        return data.get("teacher") or "Teacher"
    except (BadSignature, SignatureExpired):
        return None
