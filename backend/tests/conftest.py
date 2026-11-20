"""Shared fixtures. `db` gives the app an in-memory SQLite database with every table."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app


@compiles(JSONB, "sqlite")
def _jsonb_as_sqlite_json(type_, compiler, **kw):
    return "JSON"


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def session():
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = session
    yield factory
    app.dependency_overrides.clear()
