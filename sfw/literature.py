import re
from html import unescape
from html.parser import HTMLParser

import requests

CROSSREF = "https://api.crossref.org/works"


class _TextExtractor(HTMLParser):
    """Convert Crossref HTML/JATS abstract markup into readable plain text."""

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data and data.strip():
            self.parts.append(data.strip())


def clean_abstract(value):
    """Return readable abstract text; Crossref abstracts may contain markup."""
    if not value:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(str(value))
        text = " ".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", unescape(text)).strip()


def search_crossref(query, rows=8):
    """Search Crossref publication metadata, including an abstract when supplied."""
    if not query or not query.strip():
        return []
    response = requests.get(
        CROSSREF,
        params={"query": query.strip(), "rows": min(max(int(rows), 1), 20)},
        headers={"User-Agent": "ScienceFairWinner/1.0 (educational research assistant)"},
        timeout=20,
    )
    response.raise_for_status()
    items = response.json().get("message", {}).get("items", [])
    results = []
    for item in items:
        title = (item.get("title") or ["Untitled"])[0]
        authors = item.get("author") or []
        author_text = ", ".join(
            " ".join(filter(None, [a.get("given"), a.get("family")]))
            for a in authors[:5]
        )
        results.append({
            "title": title,
            "authors": author_text or "Author information not supplied",
            "year": (item.get("published", {}).get("date-parts") or [[None]])[0][0],
            "journal": (item.get("container-title") or [""])[0],
            "doi": item.get("DOI", ""),
            "url": item.get("URL", ""),
            "type": item.get("type", ""),
            "abstract": clean_abstract(item.get("abstract", "")),
        })
    return results


def _markdown_safe(value):
    """Escape common Markdown control characters in external metadata."""
    value = str(value or "").replace("\\", "\\\\")
    for char in (chr(96), "*", "_", "[", "]"):
        value = value.replace(char, "\\" + char)
    return value.replace("\n", " ").strip()


def format_references(sources):
    """Build a reference list only from records actually returned by Crossref."""
    if not sources:
        return ""
    lines = [
        "**Crossref records retrieved**",
        "_These are publication metadata records, not confirmation that the full papers were read or independently verified._",
    ]
    for index, item in enumerate(sources, start=1):
        authors = _markdown_safe(item.get("authors") or "Author information not supplied")
        year = _markdown_safe(item.get("year") or "n.d.")
        title = _markdown_safe(item.get("title") or "Untitled")
        journal = _markdown_safe(item.get("journal"))
        detail = f"{authors} ({year}). {title}."
        if journal:
            detail += f" {journal}."
        doi = str(item.get("doi") or "").strip()
        url = str(item.get("url") or "").strip()
        if doi:
            detail += f" [https://doi.org/{doi}](https://doi.org/{doi})"
        elif url.startswith(("https://", "http://")):
            detail += f" [Publication record]({url})"
        lines.append(f"{index}. {detail}")
    return "\n\n" + "\n".join(lines)


def unmatched_citation_numbers(answer, sources):
    """Return citation numbers in the AI answer that have no retrieved Crossref record."""
    valid_count = len(sources or [])
    cited = {int(number) for number in re.findall(r"\\[(\\d+)\\]", answer or "")}
    return sorted(number for number in cited if number < 1 or number > valid_count)
