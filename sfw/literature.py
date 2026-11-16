import re
from urllib.parse import quote, urlparse
from html import unescape
from html.parser import HTMLParser

import requests

CROSSREF = "https://api.crossref.org/works"

AFRICA_TERMS = (
    "africa", "african", "kenya", "uganda", "tanzania", "ethiopia", "rwanda",
    "burundi", "nigeria", "ghana", "malawi", "zambia", "zimbabwe", "mozambique",
    "south africa", "cameroon", "senegal", "mali", "niger", "burkina faso",
    "ivory coast", "cote d'ivoire", "benin", "togo", "sierra leone", "liberia",
    "gambia", "sudan", "south sudan", "somalia", "eritrea", "djibouti",
    "democratic republic of the congo", "congo", "angola", "botswana", "namibia",
    "lesotho", "eswatini", "madagascar", "mauritius", "seychelles", "egypt",
    "morocco", "algeria", "tunisia", "libya", "chad", "central african republic",
    "gabon", "equatorial guinea", "comoros", "maize belt",
)


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


def _safe_http_url(value):
    value = str(value or "").strip()
    parsed = urlparse(value)
    return value if parsed.scheme in ("http", "https") and parsed.netloc else ""


def doi_url(value):
    """Build a safe DOI resolver URL from Crossref metadata."""
    doi = str(value or "").strip()
    return "https://doi.org/" + quote(doi, safe="/") if doi else ""


def _publication_year(item):
    for field in ("published", "published-print", "published-online", "issued", "created"):
        date_parts = (item.get(field) or {}).get("date-parts") or []
        if date_parts and date_parts[0]:
            return date_parts[0][0]
    return None


def _record_from_crossref(item):
    title = (item.get("title") or ["Untitled"])[0]
    authors = item.get("author") or []
    author_text = ", ".join(
        " ".join(filter(None, [a.get("given"), a.get("family")]))
        for a in authors
        if isinstance(a, dict)
    )
    affiliations = []
    for author in authors:
        if isinstance(author, dict):
            for affiliation in author.get("affiliation") or []:
                if isinstance(affiliation, dict):
                    affiliations.append(affiliation.get("name", ""))
    return {
        "title": title,
        "authors": author_text or "Author information not supplied",
        "year": _publication_year(item),
        "journal": (item.get("container-title") or [""])[0],
        "doi": str(item.get("DOI") or "").strip(),
        "url": _safe_http_url(item.get("URL", "")),
        "type": item.get("type", ""),
        "abstract": clean_abstract(item.get("abstract", "")),
        "affiliations": "; ".join(x for x in affiliations if x),
    }


def _africa_signal(record):
    text = " ".join(str(record.get(k) or "") for k in ("title", "abstract", "affiliations", "journal")).lower()
    hits = [term for term in AFRICA_TERMS if term in text]
    return hits


def _topic_score(record, query):
    terms = [t for t in re.findall(r"[a-z0-9]+", str(query).lower()) if len(t) > 2]
    title = str(record.get("title") or "").lower()
    abstract = str(record.get("abstract") or "").lower()
    return sum(3 for t in terms if t in title) + sum(1 for t in terms if t in abstract)


def search_crossref(query, rows=8, start_year=None, end_year=None,
                    africa_first=False, article_only=True):
    """Search Crossref and locally screen, de-duplicate and rank metadata records.

    Geographic ranking is a text signal, not proof of study location. Users should
    confirm the study setting in the publisher abstract or full text.
    """
    if not query or not str(query).strip():
        return []
    try:
        row_count = min(max(int(rows), 1), 20)
        start_year = int(start_year) if start_year is not None else None
        end_year = int(end_year) if end_year is not None else None
    except (TypeError, ValueError):
        raise ValueError("Record count and publication years must be valid numbers.")
    if start_year and end_year and start_year > end_year:
        raise ValueError("The start year must not be later than the end year.")

    filters = []
    if start_year:
        filters.append(f"from-pub-date:{start_year}-01-01")
    if end_year:
        filters.append(f"until-pub-date:{end_year}-12-31")
    params = {"query": str(query).strip(), "rows": min(row_count * 5, 100),
              "select": "DOI,title,author,published,published-print,published-online,issued,created,container-title,type,abstract,URL"}
    if filters:
        params["filter"] = ",".join(filters)

    response = requests.get(
        CROSSREF, params=params,
        headers={"User-Agent": "ScienceFairWinner/1.2 (educational research assistant)"},
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    if not isinstance(items, list):
        raise ValueError("Crossref returned an unexpected publication-record format.")

    allowed_types = {"journal-article", "proceedings-article", "posted-content", "book-chapter"}
    results, seen = [], set()
    for raw in items:
        if not isinstance(raw, dict):
            continue
        record = _record_from_crossref(raw)
        year = record.get("year")
        if start_year and (not year or year < start_year):
            continue
        if end_year and (not year or year > end_year):
            continue
        if article_only and record["type"] not in allowed_types:
            continue
        identity = record["doi"].lower() or re.sub(r"\W+", "", record["title"].lower())
        if identity in seen:
            continue
        seen.add(identity)
        record["africa_matches"] = _africa_signal(record)
        record["africa_relevance"] = bool(record["africa_matches"])
        record["topic_score"] = _topic_score(record, query)
        results.append(record)

    results.sort(
        key=lambda r: (bool(r["africa_relevance"]) if africa_first else False,
                       r["topic_score"], bool(r["abstract"]), bool(r["doi"])),
        reverse=True,
    )
    return results[:row_count]


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
            resolver_url = doi_url(doi)
            detail += f" [https://doi.org/{_markdown_safe(doi)}]({resolver_url})"
        elif _safe_http_url(url):
            detail += f" [Publication record]({url})"
        lines.append(f"{index}. {detail}")
    return "\n\n" + "\n".join(lines)


def unmatched_citation_numbers(answer, sources):
    """Return citation numbers in the AI answer that have no retrieved Crossref record."""
    valid_count = len(sources or [])
    cited = {int(number) for number in re.findall(r"\[(\d+)\]", answer or "")}
    return sorted(number for number in cited if number < 1 or number > valid_count)
