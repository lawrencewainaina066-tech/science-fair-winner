import json, re
from pathlib import Path
from .config import PROJECT_DIR

def slugify(text):
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.strip()).strip("-").lower()
    return s[:60] or "science-project"

def save_project(title, payload):
    path = PROJECT_DIR / f"{slugify(title)}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

def list_projects():
    return sorted(PROJECT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

def read_project(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
