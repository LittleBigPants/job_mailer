"""LLM-based email generation for the job-mailer pipeline."""
from __future__ import annotations

import os
import re

import groq
import typer
from groq import Groq

from job_mailer.models import CompanyRecord, Status

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLICHE_DENY_LIST = [
    "i hope this finds you",
    "quick question",
    "synergy",
    "touch base",
    "circle back",
]

_WORD_MIN = 60
_WORD_MAX = 180

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _word_count(text: str) -> int:
    return len(text.split())


def _has_brackets(text: str) -> bool:
    return re.search(r"\[.+?\]", text) is not None


def _has_cliche(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in CLICHE_DENY_LIST)


def _validate(text: str) -> str | None:
    """Return a failure reason string if the text is invalid, or None if valid.

    Check order: word count first, then brackets, then cliche.
    """
    wc = _word_count(text)
    if wc < _WORD_MIN or wc > _WORD_MAX:
        return f"The previous message was {wc} words. Target: 60-180."
    if _has_brackets(text):
        return "The previous message contained [bracket] placeholders. Remove them."
    if _has_cliche(text):
        return "The previous message started with a cliche opener. Avoid those."
    return None


def _build_messages(record: CompanyRecord, profile: dict) -> list[dict]:
    """Build the initial system + user messages list for the Groq API call."""
    developer = profile.get("developer", {})
    dev_name = developer.get("name", "")
    dev_title = developer.get("title", "")
    skills = developer.get("skills", {})
    primary_skills = ", ".join(skills.get("primary", []))
    specialisation = skills.get("specialisation", "")
    contact = developer.get("contact", {})
    contact_email = contact.get("email", "")

    system_prompt = (
        "You write personalized cold email introductions on behalf of software developers "
        "reaching out to companies about potential job opportunities. "
        "Your emails are professional but warm, never salesy or generic. "
        "Each email must be 60-180 words, contain no cliche openers (e.g. 'I hope this finds you', "
        "'touch base', 'circle back', 'synergy', 'quick question'), "
        "and must contain no bracket placeholders like [Company] or [Role]. "
        "End with a soft ask — a brief mention of interest in available roles or a short chat."
    )

    user_prompt = (
        f"Write a personalized cold email introduction for the following company:\n\n"
        f"Company name: {record.company_name}\n"
        f"Company URL: {record.url}\n\n"
        f"Please infer the industry from the URL domain.\n\n"
        f"The email is from:\n"
        f"Name: {dev_name}\n"
        f"Title: {dev_title}\n"
        f"Primary skills: {primary_skills}\n"
        f"Specialisation: {specialisation}\n"
        f"Contact email: {contact_email}\n\n"
        f"Write only the email body (no subject line, no greeting line like 'Dear ...'). "
        f"60-180 words, no bracket placeholders, no cliche openers."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_email(record: CompanyRecord, profile: dict) -> CompanyRecord:
    """Call Groq to generate a personalized cold email intro for *record*.

    - On valid first-attempt response: sets record.generated_message and
      record.status = Status.PENDING.
    - On first-attempt validation failure: retries once with an embedded
      failure reason appended to the message history.
    - On double failure or caught Groq API error: sets
      record.status = Status.GENERATION_FAILED (never raises).
    """
    model_name = profile.get("generation", {}).get("model", "llama-3.3-70b-versatile")
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    messages = _build_messages(record, profile)

    try:
        # First attempt
        response1 = client.chat.completions.create(
            messages=messages,
            model=model_name,
            max_completion_tokens=300,
        )
        text1 = response1.choices[0].message.content

        failure_reason = _validate(text1)
        if failure_reason is None:
            record.generated_message = text1
            record.status = Status.PENDING
            return record

        # Retry with embedded failure reason
        messages.append({"role": "assistant", "content": text1})
        messages.append({"role": "user", "content": failure_reason})

        response2 = client.chat.completions.create(
            messages=messages,
            model=model_name,
            max_completion_tokens=300,
        )
        text2 = response2.choices[0].message.content

        failure_reason2 = _validate(text2)
        if failure_reason2 is None:
            record.generated_message = text2
            record.status = Status.PENDING
            return record

        # Both attempts failed
        reason = failure_reason2

    except (groq.APIConnectionError, groq.RateLimitError, groq.APIStatusError) as exc:
        reason = str(exc)

    typer.echo(
        f"WARNING: generation_failed for {record.url} ({reason})", err=True
    )
    record.status = Status.GENERATION_FAILED
    return record
