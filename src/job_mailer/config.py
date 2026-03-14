# Source: python-dotenv 1.2.2 (https://pypi.org/project/python-dotenv/)
# src/job_mailer/config.py
from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # loads .env relative to cwd; no-op if absent

_REQUIRED_ENV_KEYS = ["GROQ_API_KEY", "RESEND_API_KEY", "RESEND_FROM_EMAIL"]
_PROFILE_PATH = Path("profile.toml")


def check_env() -> None:
    """Raise SystemExit with actionable message if required env vars are missing."""
    missing = [k for k in _REQUIRED_ENV_KEYS if not os.environ.get(k)]
    if missing:
        keys_list = "\n  ".join(missing)
        sys.exit(
            f"Error: missing required environment variable(s):\n  {keys_list}\n"
            f"\nCopy .env.example to .env and fill in the values."
        )


def load_profile(path: Path = _PROFILE_PATH) -> dict:
    """Load and return developer profile from TOML file."""
    if not path.exists():
        sys.exit(
            f"Error: profile file not found at '{path}'.\n"
            f"Copy profile.example.toml to profile.toml and fill in your details."
        )
    with open(path, "rb") as f:
        return tomllib.load(f)
