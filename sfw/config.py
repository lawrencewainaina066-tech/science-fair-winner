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

def ai_settings():
    return {
        "provider": os.getenv("SFW_AI_PROVIDER", "").strip().lower(),
        "anthropic_key": os.getenv("ANTHROPIC_API_KEY", "").strip(),
        "anthropic_model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        "openai_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    }
