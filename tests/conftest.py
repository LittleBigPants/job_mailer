"""Shared pytest fixtures for job_mailer tests."""
import pytest


_ENV_KEYS = ["GROQ_API_KEY", "RESEND_API_KEY", "RESEND_FROM_EMAIL"]


@pytest.fixture(autouse=True)
def clear_env_keys(monkeypatch):
    """Remove the three required env var keys before each test to prevent pollution."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
