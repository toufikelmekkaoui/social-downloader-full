"""
tests/conftest.py
-----------------
Shared pytest fixtures.
"""

import os
import pytest

# Make sure we run in testing mode
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")


@pytest.fixture(scope="session")
def app():
    """Create a Flask test application."""
    from app.factory import create_app
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture(scope="session")
def client(app):
    """Return a Flask test client."""
    return app.test_client()
