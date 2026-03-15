"""Tests for job_mailer.generator — TDD RED state.

These tests cover GEN-01 through GEN-04. They fail with ModuleNotFoundError
until Plan 02 creates src/job_mailer/generator.py.
"""
from unittest.mock import MagicMock, patch

from job_mailer.models import CompanyRecord, Status
from job_mailer.generator import generate_email  # noqa: F401 — fails until Plan 02


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record() -> CompanyRecord:
    return CompanyRecord(
        url="https://stripe.com",
        company_name="Stripe",
        email_found="jobs@stripe.com",
    )


def _make_profile(model: str | None = None) -> dict:
    profile: dict = {
        "developer": {
            "name": "Jane Smith",
            "title": "Senior Software Engineer",
            "location": "Berlin, Germany",
            "years_experience": 8,
            "contact": {
                "email": "jane@example.com",
                "github": "https://github.com/jsmith",
                "linkedin": "",
                "portfolio": "",
            },
            "skills": {
                "primary": ["Python", "TypeScript", "Go"],
                "specialisation": "backend APIs and data pipelines",
            },
        },
        "send": {"delay_seconds": 2},
    }
    if model is not None:
        profile["generation"] = {"model": model}
    return profile


def _mock_response(content: str) -> MagicMock:
    response = MagicMock()
    response.choices[0].message.content = content
    return response


# ---------------------------------------------------------------------------
# GEN-01: successful generation
# ---------------------------------------------------------------------------

def test_generate_email_success(monkeypatch):
    """Groq returns a valid 80-word message → record.generated_message is set, status PENDING."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    valid_message = " ".join(["word"] * 80)
    mock_resp = _mock_response(valid_message)
    with patch("job_mailer.generator.Groq") as mock_groq_cls:
        mock_groq_cls.return_value.chat.completions.create.return_value = mock_resp
        record = _make_record()
        profile = _make_profile()
        result = generate_email(record, profile)
    assert result.generated_message == valid_message
    assert result.status == Status.PENDING


# ---------------------------------------------------------------------------
# GEN-01: prompt content
# ---------------------------------------------------------------------------

def test_prompt_includes_company_signals(monkeypatch):
    """The messages sent to Groq must contain company_name, url, and 'industry'."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    valid_message = " ".join(["word"] * 80)
    mock_resp = _mock_response(valid_message)
    with patch("job_mailer.generator.Groq") as mock_groq_cls:
        mock_create = mock_groq_cls.return_value.chat.completions.create
        mock_create.return_value = mock_resp
        record = _make_record()
        profile = _make_profile()
        generate_email(record, profile)
        call_kwargs = mock_create.call_args
    messages = call_kwargs[1].get("messages") or call_kwargs[0][0]
    concatenated = " ".join(m["content"] for m in messages)
    assert "Stripe" in concatenated
    assert "stripe.com" in concatenated
    assert "industry" in concatenated.lower()


# ---------------------------------------------------------------------------
# GEN-02: bracket placeholder retry
# ---------------------------------------------------------------------------

def test_retry_on_brackets(monkeypatch):
    """First response contains '[Name]' → Groq called twice; second call includes 'bracket'."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    bad_resp = _mock_response(" ".join(["word"] * 80) + " [Name] placeholder")
    good_resp = _mock_response(" ".join(["word"] * 80))
    with patch("job_mailer.generator.Groq") as mock_groq_cls:
        mock_create = mock_groq_cls.return_value.chat.completions.create
        mock_create.side_effect = [bad_resp, good_resp]
        result = generate_email(_make_record(), _make_profile())
    assert mock_create.call_count == 2
    retry_messages = mock_create.call_args_list[1][1].get("messages") or mock_create.call_args_list[1][0][0]
    retry_text = " ".join(m["content"] for m in retry_messages).lower()
    assert "bracket" in retry_text


# ---------------------------------------------------------------------------
# GEN-02: word-count retry
# ---------------------------------------------------------------------------

def test_retry_on_word_count(monkeypatch):
    """First response is 10 words (too short) → Groq called twice; second call includes '10 words'."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    bad_resp = _mock_response(" ".join(["word"] * 10))
    good_resp = _mock_response(" ".join(["word"] * 80))
    with patch("job_mailer.generator.Groq") as mock_groq_cls:
        mock_create = mock_groq_cls.return_value.chat.completions.create
        mock_create.side_effect = [bad_resp, good_resp]
        result = generate_email(_make_record(), _make_profile())
    assert mock_create.call_count == 2
    retry_messages = mock_create.call_args_list[1][1].get("messages") or mock_create.call_args_list[1][0][0]
    retry_text = " ".join(m["content"] for m in retry_messages)
    assert "10 words" in retry_text


# ---------------------------------------------------------------------------
# GEN-02: cliché opener retry
# ---------------------------------------------------------------------------

def test_retry_on_cliche(monkeypatch):
    """First response contains 'touch base' → Groq called twice; second call includes 'cliche' or 'opener'."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    bad_resp = _mock_response(" ".join(["word"] * 80) + " I wanted to touch base")
    good_resp = _mock_response(" ".join(["word"] * 80))
    with patch("job_mailer.generator.Groq") as mock_groq_cls:
        mock_create = mock_groq_cls.return_value.chat.completions.create
        mock_create.side_effect = [bad_resp, good_resp]
        result = generate_email(_make_record(), _make_profile())
    assert mock_create.call_count == 2
    retry_messages = mock_create.call_args_list[1][1].get("messages") or mock_create.call_args_list[1][0][0]
    retry_text = " ".join(m["content"] for m in retry_messages).lower()
    assert "cliche" in retry_text or "opener" in retry_text


# ---------------------------------------------------------------------------
# GEN-03 / GEN-04: double failure
# ---------------------------------------------------------------------------

def test_double_failure_returns_generation_failed(monkeypatch):
    """Both responses contain '[bracket]' → record.status == GENERATION_FAILED, no exception."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    bad_resp1 = _mock_response(" ".join(["word"] * 80) + " [Company] placeholder")
    bad_resp2 = _mock_response(" ".join(["word"] * 80) + " [Role] placeholder")
    with patch("job_mailer.generator.Groq") as mock_groq_cls:
        mock_create = mock_groq_cls.return_value.chat.completions.create
        mock_create.side_effect = [bad_resp1, bad_resp2]
        result = generate_email(_make_record(), _make_profile())
    assert result.status == Status.GENERATION_FAILED


# ---------------------------------------------------------------------------
# GEN-01: model name from config
# ---------------------------------------------------------------------------

def test_model_name_from_config(monkeypatch):
    """profile['generation']['model'] = 'test-model-name' → that name is passed to Groq."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    valid_message = " ".join(["word"] * 80)
    mock_resp = _mock_response(valid_message)
    with patch("job_mailer.generator.Groq") as mock_groq_cls:
        mock_create = mock_groq_cls.return_value.chat.completions.create
        mock_create.return_value = mock_resp
        profile = _make_profile(model="test-model-name")
        generate_email(_make_record(), profile)
        call_kwargs = mock_create.call_args
    model_used = call_kwargs[1].get("model") or call_kwargs[0][1]
    assert model_used == "test-model-name"
