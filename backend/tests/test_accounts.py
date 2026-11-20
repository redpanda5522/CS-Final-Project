"""Accounts, sessions, lockout, password changes and resets, and analysis ownership.

Uses the in-memory SQLite database from conftest.py.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import Analysis, PasswordResetToken, User, UserSession
from app.services import accounts, mailer

NEW_ACCOUNT = {"name": " Ada Lovelace ", "email": " Ada@Example.com ", "organization": "", "password": "correct horse"}


@pytest.fixture
def client(db):
    return TestClient(app)


def test_create_account_signs_in_and_normalizes(client, db):
    response = client.post("/api/accounts", json=NEW_ACCOUNT)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ada Lovelace" and body["email"] == "ada@example.com"
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert client.get("/api/accounts/me").json() == body
    with db() as s:
        user = s.scalar(select(User))
        assert "correct horse" not in user.password_hash
        token_hash = s.scalar(select(UserSession.token_hash))
    assert client.cookies["session"] not in token_hash


def test_duplicate_email_is_rejected(client):
    client.post("/api/accounts", json=NEW_ACCOUNT)
    response = client.post("/api/accounts", json={**NEW_ACCOUNT, "email": "ADA@example.com"})
    assert response.status_code == 409


@pytest.mark.parametrize("change", [{"password": "short"}, {"email": "not-an-email"}, {"name": "   "}])
def test_invalid_account_is_rejected(client, change):
    assert client.post("/api/accounts", json={**NEW_ACCOUNT, **change}).status_code == 422


def test_sign_in_and_sign_out(db):
    TestClient(app).post("/api/accounts", json=NEW_ACCOUNT)
    client = TestClient(app)
    assert client.get("/api/accounts/me").status_code == 401
    wrong = client.post("/api/accounts/sign-in", json={"email": "ada@example.com", "password": "wrong password"})
    assert wrong.status_code == 401
    unknown = client.post("/api/accounts/sign-in", json={"email": "bob@example.com", "password": "correct horse"})
    assert unknown.status_code == 401
    signed_in = client.post("/api/accounts/sign-in", json={"email": "ADA@example.com", "password": "correct horse"})
    assert signed_in.status_code == 200
    token = client.cookies["session"]
    assert client.get("/api/accounts/me").status_code == 200

    assert client.post("/api/accounts/sign-out").status_code == 204
    assert client.get("/api/accounts/me").status_code == 401
    # The old token no longer works even if a client kept it.
    client.cookies.set("session", token)
    assert client.get("/api/accounts/me").status_code == 401


def test_expired_session_is_rejected(client, db):
    client.post("/api/accounts", json=NEW_ACCOUNT)
    with db() as s:
        s.scalar(select(UserSession)).expires_at = datetime.now(UTC) - timedelta(seconds=1)
        s.commit()
    assert client.get("/api/accounts/me").status_code == 401


def test_training_accepts_signed_in_user(client):
    upload = {"file": ("data.csv", b"signal,recur\n1,0\n2,1\n")}
    form = {"target_column": "recur", "model_name": "logistic"}
    assert client.post("/api/analyses/train", data=form, files=upload).status_code == 401
    client.post("/api/accounts", json=NEW_ACCOUNT)
    # Past the sign-in check: rejected for the model choice instead.
    response = client.post("/api/analyses/train", data=form, files=upload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Only XGBoost training is supported."


def test_password_hash_round_trip():
    stored = accounts.hash_password("correct horse")
    assert accounts.verify_password("correct horse", stored)
    assert not accounts.verify_password("correct horsf", stored)
    assert not accounts.verify_password("x", "garbage")


def _sign_in(client, password="correct horse", email="ada@example.com"):
    return client.post("/api/accounts/sign-in", json={"email": email, "password": password})


def _lock_reset_time(db, moment):
    with db() as s:
        s.scalar(select(User)).locked_until = moment
        s.commit()


def test_repeated_wrong_passwords_lock_the_account(db):
    TestClient(app).post("/api/accounts", json=NEW_ACCOUNT)
    client = TestClient(app)
    for _ in range(accounts.MAX_FAILED_SIGN_INS):
        assert _sign_in(client, "wrong password").status_code == 401
    locked = _sign_in(client)  # Even the right password is refused while locked.
    assert locked.status_code == 429
    assert 0 < int(locked.headers["retry-after"]) <= 15 * 60
    assert "15 minutes" in locked.json()["detail"]

    _lock_reset_time(db, datetime.now(UTC) - timedelta(seconds=1))
    assert _sign_in(client).status_code == 200


def test_a_successful_sign_in_resets_the_failure_count(db):
    TestClient(app).post("/api/accounts", json=NEW_ACCOUNT)
    client = TestClient(app)
    for _ in range(accounts.MAX_FAILED_SIGN_INS - 1):
        _sign_in(client, "wrong password")
    assert _sign_in(client).status_code == 200
    for _ in range(accounts.MAX_FAILED_SIGN_INS - 1):
        _sign_in(client, "wrong password")
    assert _sign_in(client).status_code == 200


def test_unknown_email_is_never_locked(client):
    for _ in range(accounts.MAX_FAILED_SIGN_INS + 1):
        assert _sign_in(client, email="nobody@example.com").status_code == 401


def test_change_password_signs_out_other_sessions(db):
    me = TestClient(app)
    me.post("/api/accounts", json=NEW_ACCOUNT)
    other = TestClient(app)
    _sign_in(other)
    wrong = me.post("/api/accounts/password", json={"currentPassword": "nope nope", "newPassword": "new password 1"})
    assert wrong.status_code == 403
    assert me.post("/api/accounts/password", json={"currentPassword": "correct horse", "newPassword": "short"}).status_code == 422

    changed = me.post("/api/accounts/password", json={"currentPassword": "correct horse", "newPassword": "new password 1"})
    assert changed.status_code == 204
    assert me.get("/api/accounts/me").status_code == 200
    assert other.get("/api/accounts/me").status_code == 401
    assert _sign_in(TestClient(app)).status_code == 401
    assert _sign_in(TestClient(app), "new password 1").status_code == 200


def test_change_password_requires_sign_in(client):
    response = client.post("/api/accounts/password", json={"currentPassword": "x", "newPassword": "new password 1"})
    assert response.status_code == 401


@pytest.fixture
def sent(monkeypatch):
    """Reset emails, captured instead of sent: [(email, token)]."""
    outbox = []
    monkeypatch.setattr(mailer, "send_password_reset", lambda email, token: outbox.append((email, token)))
    return outbox


def _request_reset(client, email="ADA@example.com"):
    return client.post("/api/accounts/password-reset", json={"email": email})


def test_reset_request_does_not_reveal_accounts(client, sent):
    client.post("/api/accounts", json=NEW_ACCOUNT)
    known, unknown = _request_reset(client), _request_reset(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert [email for email, _ in sent] == ["ada@example.com"]
    # A second request within a minute sends nothing, but answers the same.
    assert _request_reset(client).json() == known.json()
    assert len(sent) == 1


def test_password_reset_flow(db, sent):
    me = TestClient(app)
    me.post("/api/accounts", json=NEW_ACCOUNT)
    for _ in range(accounts.MAX_FAILED_SIGN_INS):
        _sign_in(TestClient(app), "wrong password")
    _request_reset(me)
    token = sent[0][1]
    with db() as s:
        assert token not in s.scalar(select(PasswordResetToken.token_hash))

    reset = me.post("/api/accounts/password-reset/confirm", json={"token": token, "newPassword": "brand new pass"})
    assert reset.status_code == 204
    assert me.get("/api/accounts/me").status_code == 401  # Every session signed out.
    assert _sign_in(TestClient(app)).status_code == 401
    assert _sign_in(TestClient(app), "brand new pass").status_code == 200  # Lockout cleared.
    again = me.post("/api/accounts/password-reset/confirm", json={"token": token, "newPassword": "another pass 1"})
    assert again.status_code == 400


def test_only_the_newest_reset_link_works(db, sent):
    TestClient(app).post("/api/accounts", json=NEW_ACCOUNT)
    client = TestClient(app)
    _request_reset(client)
    with db() as s:  # Pretend the first link is older than the one-minute limit.
        s.scalar(select(PasswordResetToken)).created_at = datetime.now(UTC) - timedelta(minutes=2)
        s.commit()
    _request_reset(client)
    (_, first), (_, second) = sent
    assert client.post("/api/accounts/password-reset/confirm", json={"token": first, "newPassword": "brand new pass"}).status_code == 400
    assert client.post("/api/accounts/password-reset/confirm", json={"token": second, "newPassword": "brand new pass"}).status_code == 204


def test_expired_reset_link_is_rejected(db, sent):
    client = TestClient(app)
    client.post("/api/accounts", json=NEW_ACCOUNT)
    _request_reset(client)
    with db() as s:
        s.scalar(select(PasswordResetToken)).expires_at = datetime.now(UTC) - timedelta(seconds=1)
        s.commit()
    response = client.post("/api/accounts/password-reset/confirm", json={"token": sent[0][1], "newPassword": "brand new pass"})
    assert response.status_code == 400


def _analyze(client):
    upload = {"file": ("procedure.csv", b"la_car,ra_car\n1,0\n")}
    response = client.post("/api/analyses/file", files=upload)
    assert response.status_code == 200
    return response.json()["analysisId"]


def test_analyses_belong_to_their_account(db):
    ada, bob = TestClient(app), TestClient(app)
    ada.post("/api/accounts", json=NEW_ACCOUNT)
    bob.post("/api/accounts", json={**NEW_ACCOUNT, "email": "bob@example.com"})
    ada_id = _analyze(ada)
    anonymous_id = _analyze(TestClient(app))

    assert [item["analysisId"] for item in ada.get("/api/analyses").json()] == [ada_id]
    assert bob.get("/api/analyses").json() == []
    assert ada.get(f"/api/analyses/{ada_id}").json()["input"] == {"la_car": 1, "ra_car": 0}
    assert bob.get(f"/api/analyses/{ada_id}").status_code == 404
    assert ada.get(f"/api/analyses/{anonymous_id}").status_code == 404
    assert TestClient(app).get("/api/analyses").status_code == 401
    with db() as s:  # The signed-out analysis is still saved, just without an owner.
        assert s.get(Analysis, anonymous_id).user_id is None
