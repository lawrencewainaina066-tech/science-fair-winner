from sfw import literature
from sfw.literature import clean_abstract, format_references, unmatched_citation_numbers


def test_clean_abstract_removes_markup_and_normalizes_whitespace():
    assert clean_abstract("<jats:p>Maize &amp; soil</jats:p>") == "Maize & soil"


def test_clean_abstract_handles_missing_value():
    assert clean_abstract("") == ""


def test_format_references_uses_only_supplied_crossref_records():
    references = format_references([{
        "authors": "A. Researcher",
        "year": 2024,
        "title": "Soil pH and maize nutrition",
        "journal": "Journal of Crop Science",
        "doi": "10.1234/example",
    }])
    assert "1. A. Researcher (2024)." in references
    assert "https://doi.org/10.1234/example" in references
    assert "full papers were read" in references


def test_format_references_returns_empty_string_without_records():
    assert format_references([]) == ""


def test_unmatched_citation_numbers_flags_only_missing_records():
    sources = [{"title": "One source"}, {"title": "Second source"}]
    assert unmatched_citation_numbers("Supported [1] and [2], unsupported [3].", sources) == [3]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_crossref_parses_year_fallback_and_cleans_abstract(monkeypatch):
    monkeypatch.setattr(literature.requests, "get", lambda *args, **kwargs: FakeResponse({
        "message": {"items": [{
            "title": ["A maize study"],
            "author": [{"given": "Ada", "family": "Example"}],
            "published-online": {"date-parts": [[2024, 3, 1]]},
            "container-title": ["Journal of Examples"],
            "DOI": "10.1234/example",
            "URL": "https://api.crossref.org/works/10.1234/example",
            "abstract": "<jats:p>Soil <jats:italic>health</jats:italic> matters.</jats:p>",
        }]}
    }))
    result = literature.search_crossref("maize", rows=8)
    assert result[0]["year"] == 2024
    assert result[0]["abstract"] == "Soil health matters."
    assert result[0]["doi"] == "10.1234/example"


def test_crossref_rejects_invalid_row_count():
    import pytest
    with pytest.raises(ValueError):
        literature.search_crossref("maize", rows="many")


def test_crossref_rejects_non_list_items(monkeypatch):
    import pytest
    monkeypatch.setattr(literature.requests, "get", lambda *args, **kwargs: FakeResponse({
        "message": {"items": "unexpected"}
    }))
    with pytest.raises(ValueError):
        literature.search_crossref("maize")


def test_reference_formatter_uses_safe_doi_url_and_escapes_title():
    output = literature.format_references([{
        "authors": "A. Author", "year": 2025, "title": "Study [draft]",
        "journal": "Science", "doi": "10.1234/a(b)",
        "url": "javascript:alert(1)",
    }])
    assert "https://doi.org/10.1234/a%28b%29" in output
    assert r"Study \[draft\]" in output
    assert "javascript:" not in output


def test_doi_url_encodes_metadata_for_safe_resolver_link():
    assert literature.doi_url("10.1234/a(b)") == "https://doi.org/10.1234/a%28b)"
