"""Accounts: create, sign in and out, change and reset passwords.

Sessions are kept in an httpOnly cookie (see app/auth.py).
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import SESSION_COOKIE, CurrentUser, clear_session_cookie, set_session_cookie
from app.db import get_session
from app.schemas import (
    Account,
    AccountCreate,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    SignInRequest,
)
from app.services import accounts, mailer

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

SessionDep = Annotated[Session, Depends(get_session)]
_UNAVAILABLE = "Accounts are unavailable right now. Please try again."


def _unavailable(session: Session, error: SQLAlchemyError) -> HTTPException:
    session.rollback()
    return HTTPException(status_code=503, detail=_UNAVAILABLE)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_account(request: AccountCreate, response: Response, session: SessionDep) -> Account:
    """Create an account and sign it in."""
    try:
        user = accounts.create_user(session, request)
        token = accounts.start_session(session, user)
    except accounts.EmailTakenError as error:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists. Sign in instead."
        ) from error
    except SQLAlchemyError as error:
        raise _unavailable(session, error) from error
    set_session_cookie(response, token)
    return accounts.to_account(user)


@router.post("/sign-in")
def sign_in(request: SignInRequest, response: Response, session: SessionDep) -> Account:
    """Sign in. Too many wrong passwords in a row lock the account for 15 minutes (429)."""
    try:
        user = accounts.authenticate(session, request.email, request.password)
        if user is None:
            raise HTTPException(status_code=401, detail="Email or password not recognized.")
        token = accounts.start_session(session, user)
    except accounts.AccountLockedError as error:
        minutes = -(-error.retry_after_seconds // 60)
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed sign-in attempts. Try again in {minutes} minute"
            f"{'' if minutes == 1 else 's'}, or reset your password.",
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    except SQLAlchemyError as error:
        raise _unavailable(session, error) from error
    set_session_cookie(response, token)
    return accounts.to_account(user)


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(request: Request, response: Response, session: SessionDep) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        try:
            accounts.end_session(session, token)
        except SQLAlchemyError as error:
            raise _unavailable(session, error) from error
    clear_session_cookie(response)


@router.get("/me")
def current_account(user: CurrentUser) -> Account:
    """The signed-in account, or 401. The frontend calls this on load to restore a session."""
    return accounts.to_account(user)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordChange, user: CurrentUser, request: Request, session: SessionDep
) -> None:
    """Change the password. Other browsers signed in to this account are signed out."""
    try:
        accounts.change_password(
            session, user, body.currentPassword, body.newPassword, request.cookies[SESSION_COOKIE]
        )
    except accounts.WrongPasswordError as error:
        raise HTTPException(status_code=403, detail="Your current password is incorrect.") from error
    except SQLAlchemyError as error:
        raise _unavailable(session, error) from error


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    body: PasswordResetRequest, background: BackgroundTasks, session: SessionDep
) -> dict[str, str]:
    """Email a reset link. Answers the same way whether or not the email has an account."""
    try:
        found = accounts.request_password_reset(session, body.email)
    except SQLAlchemyError as error:
        raise _unavailable(session, error) from error
    if found is not None:
        user, token = found
        # Sent after the response, so the response time does not reveal the account.
        background.add_task(mailer.send_password_reset, user.email, token)
    return {"detail": "If an account exists for that email, a reset link is on its way."}


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(body: PasswordResetConfirm, response: Response, session: SessionDep) -> None:
    """Set a new password from a reset link. Every session is signed out, including this
    browser's, so the user signs in again with the new password."""
    try:
        accounts.reset_password(session, body.token, body.newPassword)
    except accounts.InvalidResetTokenError as error:
        raise HTTPException(
            status_code=400, detail="This reset link is invalid or has expired. Request a new one."
        ) from error
    except SQLAlchemyError as error:
        raise _unavailable(session, error) from error
    clear_session_cookie(response)
