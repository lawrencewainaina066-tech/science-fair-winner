from sfw.literature import clean_abstract, format_references


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
    assert "[1]." not in references
    assert "A. Researcher (2024)." in references
    assert "https://doi.org/10.1234/example" in references
    assert "full papers were read" in references


def test_format_references_returns_empty_string_without_records():
    assert format_references([]) == ""
