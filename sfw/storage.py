import json
import re
from pathlib import Path

from .config import PROJECT_DIR


def slugify(text):
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(text).strip()).strip("-").lower()
    return value[:60] or "science-project"


def save_project(title, payload):
    """Save without silently overwriting an earlier project with the same title."""
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    base = slugify(title)
    path = PROJECT_DIR / f"{base}.json"
    version = 2
    while path.exists():
        path = PROJECT_DIR / f"{base}-{version}.json"
        version += 1
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def list_projects():
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(PROJECT_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def read_project(path):
    """Read a project file selected from the configured project library."""
    project_path = Path(path).resolve()
    root = PROJECT_DIR.resolve()
    if project_path.parent != root or project_path.suffix.lower() != ".json":
        raise ValueError("Project file must be a JSON file inside the configured project library.")
    return json.loads(project_path.read_text(encoding="utf-8"))
