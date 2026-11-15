import json

import pytest

from sfw import storage


def test_saving_same_title_does_not_overwrite_existing_project(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PROJECT_DIR", tmp_path)
    first = storage.save_project("Maize Growth", {"revision": 1})
    second = storage.save_project("Maize Growth", {"revision": 2})
    assert first != second
    assert json.loads(first.read_text())["revision"] == 1
    assert json.loads(second.read_text())["revision"] == 2


def test_read_project_rejects_paths_outside_library(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PROJECT_DIR", tmp_path / "projects")
    outside = tmp_path / "outside.json"
    outside.write_text('{"secret": true}')
    with pytest.raises(ValueError):
        storage.read_project(outside)


def test_project_slug_is_safe():
    assert storage.slugify("../Maize growth / 2026") == "maize-growth-2026"
