"""The signed-in user, read from the session cookie."""

import os
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.services import accounts

SESSION_COOKIE = "session"
# Set COOKIE_SECURE=true when the app is served over HTTPS.
_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "").lower() == "true"


def set_session_cookie(response: Response, token: str) -> None:
    # httponly: page scripts cannot read the token. samesite=strict: other sites cannot
    # make the browser send it, which also blocks cross-site request forgery.
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(accounts.SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="strict",
        secure=_COOKIE_SECURE,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="strict", secure=_COOKIE_SECURE, path="/")


def optional_user(request: Request, session: Annotated[Session, Depends(get_session)]) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        return accounts.user_for_token(session, token)
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="Accounts are unavailable right now.") from error


def require_user(user: Annotated[User | None, Depends(optional_user)]) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return user


CurrentUser = Annotated[User, Depends(require_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]
