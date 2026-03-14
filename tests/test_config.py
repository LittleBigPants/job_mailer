"""Unit tests for src/job_mailer/config.py — check_env() and load_profile()."""
import pytest
from pathlib import Path

from job_mailer.config import check_env, load_profile


# ---------------------------------------------------------------------------
# check_env() tests
# ---------------------------------------------------------------------------


def test_check_env_missing_key(monkeypatch):
    """check_env() raises SystemExit when GROQ_API_KEY is absent."""
    # GROQ_API_KEY already absent via autouse fixture
    with pytest.raises(SystemExit):
        check_env()


def test_check_env_all_present(monkeypatch):
    """check_env() returns None without raising when all three keys are present."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "test@example.com")
    result = check_env()
    assert result is None


def test_check_env_names_missing_key(monkeypatch):
    """check_env() error message contains the name of the missing key, not a traceback."""
    # RESEND_API_KEY is absent; set the other two
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "test@example.com")
    with pytest.raises(SystemExit) as exc_info:
        check_env()
    assert "RESEND_API_KEY" in str(exc_info.value)


# ---------------------------------------------------------------------------
# load_profile() tests
# ---------------------------------------------------------------------------


def test_load_profile_schema(tmp_path):
    """load_profile(path) returns a dict with a 'developer' key when file exists."""
    profile_file = tmp_path / "profile.toml"
    profile_file.write_text('[developer]\nname = "Test"\n')
    result = load_profile(profile_file)
    assert isinstance(result, dict)
    assert "developer" in result


def test_load_profile_missing_file(tmp_path):
    """load_profile(path) raises SystemExit with 'profile' in message when file absent."""
    missing_path = tmp_path / "nonexistent_profile.toml"
    with pytest.raises(SystemExit) as exc_info:
        load_profile(missing_path)
    assert "profile" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# validate_profile() tests — added Phase 2
# ---------------------------------------------------------------------------


def test_validate_profile_missing_field():
    """validate_profile({}) raises SystemExit; message names a missing field."""
    from job_mailer.config import validate_profile  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc_info:
        validate_profile({})
    # The error message must contain a dotted field path (e.g. "developer.name")
    assert "developer" in str(exc_info.value)


def test_validate_profile_all_present():
    """validate_profile() returns None when all required fields are present."""
    from job_mailer.config import validate_profile  # noqa: PLC0415
    valid_profile = {
        "developer": {
            "name": "A",
            "title": "B",
            "contact": {"email": "a@b.com"},
            "skills": {"primary": "Python", "specialisation": "backend"},
        }
    }
    result = validate_profile(valid_profile)
    assert result is None
