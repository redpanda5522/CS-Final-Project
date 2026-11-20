"""Account storage, password hashing, sign-in sessions, lockout, and password resets."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import PasswordResetToken, User, UserSession
from app.schemas import Account, AccountCreate

SESSION_LIFETIME = timedelta(days=7)
# After this many wrong passwords in a row, the account cannot sign in for LOCKOUT.
MAX_FAILED_SIGN_INS = 5
LOCKOUT = timedelta(minutes=15)
RESET_LIFETIME = timedelta(minutes=30)
# At most one reset email per account per minute, so the form cannot be used to spam someone.
RESET_REQUEST_INTERVAL = timedelta(minutes=1)

# scrypt settings (about 16 MiB of memory per hash), stored with each hash so they can change.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


class EmailTakenError(ValueError):
    pass


class AccountLockedError(RuntimeError):
    def __init__(self, retry_after: timedelta) -> None:
        super().__init__("Account locked")
        self.retry_after_seconds = max(1, int(retry_after.total_seconds()))


class WrongPasswordError(ValueError):
    pass


class InvalidResetTokenError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(moment: datetime) -> datetime:
    """SQLite (used by the tests) drops the time zone; Postgres keeps it."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p)
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), expected)


# Checked when the email is unknown, so a wrong email takes as long as a wrong password.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def to_account(user: User) -> Account:
    return Account(id=user.user_id, name=user.name, email=user.email, organization=user.organization)


def find_user(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.strip().lower()))


def create_user(session: Session, request: AccountCreate) -> User:
    user = User(
        user_id=str(uuid4()),
        email=request.email,
        name=request.name,
        organization=request.organization,
        password_hash=hash_password(request.password),
        failed_sign_ins=0,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise EmailTakenError(request.email) from error
    return user


def authenticate(session: Session, email: str, password: str) -> User | None:
    """Return the user, or None for a wrong email or password.

    Raises AccountLockedError while the account is locked, even for the right password,
    so guessing cannot continue during the lockout.
    """
    user = find_user(session, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    now = _now()
    if user.locked_until is not None and _aware(user.locked_until) > now:
        verify_password(password, _DUMMY_HASH)
        raise AccountLockedError(_aware(user.locked_until) - now)
    if verify_password(password, user.password_hash):
        if user.failed_sign_ins or user.locked_until:
            user.failed_sign_ins, user.locked_until = 0, None
            session.commit()
        return user
    # Increment in the database, so simultaneous attempts are all counted.
    failures = session.execute(
        update(User)
        .where(User.user_id == user.user_id)
        .values(failed_sign_ins=User.failed_sign_ins + 1)
        .returning(User.failed_sign_ins)
    ).scalar_one()
    if failures >= MAX_FAILED_SIGN_INS:
        session.execute(
            update(User)
            .where(User.user_id == user.user_id)
            .values(failed_sign_ins=0, locked_until=now + LOCKOUT)
        )
    session.commit()
    return None


def start_session(session: Session, user: User) -> str:
    """Return a new session token. Only its hash is stored, so a database leak does not
    reveal usable tokens."""
    token = secrets.token_urlsafe(32)
    now = _now()
    # Clear this user's expired sessions so the table does not grow forever.
    session.execute(
        delete(UserSession).where(UserSession.user_id == user.user_id, UserSession.expires_at < now)
    )
    session.add(
        UserSession(token_hash=_token_hash(token), user_id=user.user_id, expires_at=now + SESSION_LIFETIME)
    )
    session.commit()
    return token


def user_for_token(session: Session, token: str) -> User | None:
    row = session.get(UserSession, _token_hash(token))
    if row is None or _aware(row.expires_at) <= _now():
        return None
    return session.get(User, row.user_id)


def end_session(session: Session, token: str) -> None:
    session.execute(delete(UserSession).where(UserSession.token_hash == _token_hash(token)))
    session.commit()


def _set_password(session: Session, user: User, password: str, keep_session_token: str | None) -> None:
    """Change the password, sign out every other session, and void reset links."""
    user.password_hash = hash_password(password)
    user.failed_sign_ins, user.locked_until = 0, None
    sessions = delete(UserSession).where(UserSession.user_id == user.user_id)
    if keep_session_token is not None:
        sessions = sessions.where(UserSession.token_hash != _token_hash(keep_session_token))
    session.execute(sessions)
    session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.user_id))
    session.commit()


def change_password(
    session: Session, user: User, current_password: str, new_password: str, session_token: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise WrongPasswordError()
    _set_password(session, user, new_password, keep_session_token=session_token)


def request_password_reset(session: Session, email: str) -> tuple[User, str] | None:
    """Return (user, token) to email, or None when there is nothing to send: the email is
    unknown, or a link was sent less than a minute ago. The caller must answer the same
    way in every case, so the form does not reveal which emails have accounts."""
    user = find_user(session, email)
    if user is None:
        return None
    now = _now()
    latest = session.scalar(
        select(PasswordResetToken.created_at)
        .where(PasswordResetToken.user_id == user.user_id)
        .order_by(PasswordResetToken.created_at.desc())
        .limit(1)
    )
    if latest is not None and now - _aware(latest) < RESET_REQUEST_INTERVAL:
        return None
    # Only the newest link works.
    session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.user_id))
    token = secrets.token_urlsafe(32)
    session.add(
        PasswordResetToken(
            token_hash=_token_hash(token), user_id=user.user_id, created_at=now, expires_at=now + RESET_LIFETIME
        )
    )
    session.commit()
    return user, token


def reset_password(session: Session, token: str, new_password: str) -> User:
    row = session.get(PasswordResetToken, _token_hash(token))
    if row is None or _aware(row.expires_at) <= _now():
        raise InvalidResetTokenError()
    user = session.get(User, row.user_id)
    # Deletes the token too, so the link works only once. Signs out every session.
    _set_password(session, user, new_password, keep_session_token=None)
    return user
