# Internet Archive access — advancedsearch + metadata APIs (no API key needed)
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UA = {"User-Agent": "Kodi Internet Archive addon"}

SORTS = {
    "relevance": "",
    "downloads": "downloads desc",
    "date": "date desc",
    "title": "titleSorter asc",
}


def _get_json(url):
    req = Request(url, headers=UA)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search(query, rows=50, page=1, sort="relevance"):
    params = {"q": query, "fl[]": ["identifier", "title", "description", "year", "downloads"],
              "rows": rows, "page": page, "output": "json"}
    if SORTS.get(sort):
        params["sort[]"] = SORTS[sort]
    data = _get_json("https://archive.org/advancedsearch.php?" + urlencode(params, doseq=True))
    return data.get("response", {}).get("docs", [])


def playable_files(identifier):
    data = _get_json("https://archive.org/metadata/" + identifier)
    out = []
    for f in data.get("files", []):
        name = f.get("name", "")
        fmt = (f.get("format") or "").lower()
        if name.lower().endswith((".mp4", ".mkv", ".avi", ".webm")) and "sample" not in name.lower():
            out.append("https://archive.org/download/" + identifier + "/" + name)
        elif "mpeg4" in fmt or "h.264" in fmt:
            out.append("https://archive.org/download/" + identifier + "/" + name)
    return out
