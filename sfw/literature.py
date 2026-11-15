import requests

CROSSREF = "https://api.crossref.org/works"

def search_crossref(query, rows=8):
    """Search Crossref metadata. Requires an internet connection when the app runs."""
    if not query.strip():
        return []
    response = requests.get(CROSSREF, params={"query": query, "rows": min(max(int(rows), 1), 20)},
                            headers={"User-Agent": "ScienceFairWinner/1.0 (educational research assistant)"},
                            timeout=20)
    response.raise_for_status()
    items = response.json().get("message", {}).get("items", [])
    results = []
    for item in items:
        title = (item.get("title") or ["Untitled"])[0]
        authors = item.get("author") or []
        author_text = ", ".join(" ".join(filter(None, [a.get("given"), a.get("family")])) for a in authors[:5])
        results.append({
            "title": title,
            "authors": author_text or "Author information not supplied",
            "year": (item.get("published", {}).get("date-parts") or [[None]])[0][0],
            "journal": (item.get("container-title") or [""])[0],
            "doi": item.get("DOI", ""),
            "url": item.get("URL", ""),
            "type": item.get("type", "")
        })
    return results
