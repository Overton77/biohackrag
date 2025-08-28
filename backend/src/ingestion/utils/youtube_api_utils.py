import re
from typing import List, Dict, Any, Optional, Iterable
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------
# ID extraction
# ---------------------------------------------
def extract_video_id(value: str) -> str:
    """Return a YouTube video ID from a URL or raw 11-char ID."""
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", value or ""):
        return value

    if value.startswith(("https://youtu.be/", "http://youtu.be/")):
        return value.rstrip("/").split("/")[-1].split("?")[0]

    parsed = urlparse(value)
    if parsed.netloc.endswith("youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                return qs["v"][0]
        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/embed/")[-1].split("?")[0]

    raise ValueError(f"Could not extract a valid YouTube video ID from: {value}")


def extract_video_ids(values: Iterable[str]) -> List[str]:
    """Vectorized helper to extract multiple IDs (deduped, in order)."""
    out, seen = [], set()
    for v in values:
        vid = extract_video_id(v)
        if vid not in seen:
            out.append(vid)
            seen.add(vid)
    return out


# ---------------------------------------------
# API fetchers (use your youtube client)
# ---------------------------------------------
def _chunk(seq: List[str], n: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def fetch_video_items(
    youtube,
    video_inputs: List[str],
    parts: str = "snippet,contentDetails,statistics,status",
) -> List[Dict[str, Any]]:
    """
    Given URLs or IDs, fetch raw video 'items' from the YouTube Data API.
    - Accepts multiple inputs
    - Chunks to 50 IDs per call (API limit)
    """
    ids = extract_video_ids(video_inputs)
    if not ids:
        return []

    items: List[Dict[str, Any]] = []
    for group in _chunk(ids, 50):
        resp = youtube.videos().list(part=parts, id=",".join(group), maxResults=50).execute()
        items.extend(resp.get("items", []))
    return items


# ---------------------------------------------
# Description parsers
# ---------------------------------------------
BULLETS = r"\-\*\u2022•·‣◦"  # common bullet characters

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _normalize_time(token: str) -> str:
    """
    Normalize timestamps to HH:MM:SS.
    Accepts M:SS, MM:SS, H:MM:SS, HH:MM:SS.
    """
    token = token.strip()
    parts = token.split(":")
    if len(parts) == 2:  # MM:SS
        return f"00:{int(parts[0]):02d}:{int(parts[1]):02d}"
    if len(parts) == 3:  # H:MM:SS or HH:MM:SS
        h, m, s = parts
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
    return token  # fallback


def _line_looks_like_header(line: str) -> bool:
    t = line.strip()
    if not t:
        return True
    if t.endswith(":"):
        return True
    lowered = t.lower()
    known_headers = (
        "resources", "links", "sponsors", "timestamps", "chapters",
        "connect with", "about", "show notes", "credits", "music", "gear"
    )
    return any(lowered.startswith(h) for h in known_headers)


def _extract_section_lines(description: str, header_regexes: List[re.Pattern]) -> List[str]:
    """
    Return the contiguous block of lines AFTER the first matching header.
    Stop at a blank line or another header-like line (after we've collected at least one line).
    """
    lines = description.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        for rx in header_regexes:
            if rx.search(line):
                start_idx = i + 1
                break
        if start_idx is not None:
            break
    if start_idx is None:
        return []

    collected = []
    for j in range(start_idx, len(lines)):
        line = lines[j]
        if _line_looks_like_header(line) and collected:
            break
        if line.strip():  # ignore leading blanks right after header
            collected.append(line)
    return collected


def parse_timestamps(description: str) -> List[Dict[str, str]]:
    """
    Extract timestamps of the form:
      00:00 Title
      0:45 - Something
      01:02:03 — Long form
      • 00:20 Intro
    Anchored at start-of-line to reduce false positives.
    """
    ts_rx = re.compile(
        rf"(?mi)^[\s{BULLETS}]*(?P<time>(?:\d{{1,2}}:)?\d{{1,2}}:\d{{2}})\s*[-—–:|]*\s*(?P<desc>.+?)\s*$"
    )
    results = []
    seen = set()
    for m in ts_rx.finditer(description or ""):
        raw_t = m.group("time")
        desc = _clean(m.group("desc"))
        norm_t = _normalize_time(raw_t)
        key = (norm_t, desc.lower())
        if desc and key not in seen:
            results.append({"time": norm_t, "description": desc})
            seen.add(key)
    return results


def parse_resources(description: str) -> List[Dict[str, str]]:
    """
    Extract resource links as {url, description}.
    Uses per-line context: the text of the line minus the URL is the description.
    If no text remains, uses the domain as the description.
    """
    url_rx = re.compile(r"https?://[^\s\])>]+", re.IGNORECASE)
    results = []
    seen_urls = set()

    for line in (description or "").splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        urls = url_rx.findall(line_stripped)
        if not urls:
            continue

        for url in urls:
            if url in seen_urls:
                continue
            desc_text = _clean(line_stripped.replace(url, " ").strip())
            desc_text = re.sub(rf"^[\s{BULLETS}]+", "", desc_text).strip()
            desc_text = re.sub(r"^[–—\-:|]+", "", desc_text).strip()

            if not desc_text:
                try:
                    host = urlparse(url).netloc
                except Exception:
                    host = "Link"
                desc_text = host

            results.append({"url": url, "description": desc_text})
            seen_urls.add(url)

    return results


def parse_what_you_will_learn(description: str) -> Dict[str, List[str]]:
    """
    Look for a 'You'll learn' / 'What you will learn' section and return bullet points as claims.
    """
    headers = [
        re.compile(r"(?i)\byou[’']?ll learn\b"),
        re.compile(r"(?i)\bwhat you[’']?ll learn\b"),
        re.compile(r"(?i)\bwhat you will learn\b"),
        re.compile(r"(?i)\byou will learn\b"),
        re.compile(r"(?i)\bkey takeaways\b"),
        re.compile(r"(?i)\btakeaways\b"),
    ]
    lines = _extract_section_lines(description or "", headers)
    if not lines:
        return {"claims": []}

    claims = []
    for line in lines:
        t = line.strip()
        if not t:
            continue
        if _line_looks_like_header(t) and claims:
            break

        bullet_pref = re.compile(rf"^\s*[{BULLETS}]+\s*(.+)$")
        m = bullet_pref.match(t)
        if m:
            claim = _clean(m.group(1))
            if claim:
                claims.append(claim)
            continue

        if not re.search(r"https?://", t):
            claims.append(_clean(t))

    seen = set()
    deduped = []
    for c in claims:
        if c and c.lower() not in seen:
            deduped.append(c)
            seen.add(c.lower())

    return {"claims": deduped}


# ---------------------------------------------
# Builder(s)
# ---------------------------------------------
def _to_int(x: Optional[str]) -> int:
    try:
        return int(x) if x is not None else 0
    except (ValueError, TypeError):
        return 0


def build_video_dict(video_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert one raw API 'item' into your requested structure:
      {
        "resources": [{ "url": ..., "description": ... }, ...],
        "timestamps": [{ "time": ..., "description": ... }, ...],
        "what_you_will_learn": { "claims": [...] },
        "title": "...",
        "publish_date": "YYYY-MM-DDTHH:MM:SSZ",
        "Views": int,
        "Likes": int,
        "Comments": int,
        "full_description": "..."
      }
    """
    snippet = (video_item or {}).get("snippet", {}) or {}
    stats = (video_item or {}).get("statistics", {}) or {}

    full_desc = snippet.get("description") or ""

    return {
        "resources": parse_resources(full_desc),
        "timestamps": parse_timestamps(full_desc),
        "what_you_will_learn": parse_what_you_will_learn(full_desc),
        "title": snippet.get("title") or "",
        "publish_date": snippet.get("publishedAt") or "",
        "Views": _to_int(stats.get("viewCount")),
        "Likes": _to_int(stats.get("likeCount")),     # 0 if hidden
        "Comments": _to_int(stats.get("commentCount")),
        "full_description": full_desc,
    }


# ---------------------------------------------
# Public, user-facing fetchers
# ---------------------------------------------
def get_video_data(youtube, video_input: str) -> Dict[str, Any]:
    """
    Fetch one video's data dict from a URL or ID.
    """
    items = fetch_video_items(youtube, [video_input])
    return build_video_dict(items[0]) if items else {}


def get_videos_data(youtube, video_inputs: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch many videos' data dicts from a list of URLs or IDs.
    Preserves input order where possible.
    """
    ids = extract_video_ids(video_inputs)
    if not ids:
        return []

    # Fetch all items (unordered) then map by id
    items = fetch_video_items(youtube, ids)
    by_id = {it.get("id"): it for it in items}

    out = []
    for vid in ids:
        it = by_id.get(vid)
        if it:
            out.append(build_video_dict(it))
    return out 

# you already have:
# youtube = build("youtube", "v3", credentials=credentials)

# video_url = "https://www.youtube.com/watch?v=pQWfxAuFe1o"

# data = get_video_data(youtube, video_url)
# print(data["title"])
# print(data["publish_date"])
# print(data["Views"], data["Likes"], data["Comments"])
# print(data["timestamps"][:3])         # first 3 timestamps
# print(data["resources"][:3])          # first 3 resources
# print(data["what_you_will_learn"])
# full text:
# print(data["full_description"])

# For multiple:
# many = get_videos_data(youtube, [video_url, "https://youtu.be/EjZPGbZDJx8"])
# print(many) 

if __name__ == "__main__":  
    print("importing youtube api utils from youtube_api_utils.py")  