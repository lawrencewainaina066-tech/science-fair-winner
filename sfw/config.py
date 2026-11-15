from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PROJECT_DIR = Path(os.getenv("SFW_PROJECT_DIR", str(ROOT / "data" / "projects")))
PROJECT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

APP_NAME = "Science Fair Winner"
APP_TAGLINE = "Scientific Intelligence and Problem-Solving Platform"


def _setting(name, default=""):
    """Read a setting from environment/.env first, then Streamlit Secrets."""
    value = os.getenv(name)
    if value:
        return value.strip()
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return str(value).strip()


def ai_settings():
    return {
        "provider": _setting("SFW_AI_PROVIDER").lower(),
        "gemini_key": _setting("GEMINI_API_KEY"),
        "gemini_model": _setting("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "anthropic_key": _setting("ANTHROPIC_API_KEY"),
        "anthropic_model": _setting("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        "openai_key": _setting("OPENAI_API_KEY"),
        "openai_model": _setting("OPENAI_MODEL", "gpt-6-luna"),
    }
