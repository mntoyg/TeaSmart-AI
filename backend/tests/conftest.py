"""Shared pytest fixtures for the TeaSmart AI backend."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def app():
    """The application itself, for tests that override a dependency.

    One instance shared with `client` in the same test, so an override
    installed on it is the one the request goes through.
    """
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
