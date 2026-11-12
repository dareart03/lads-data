"""Shared helpers for the LADS data scripts.

Talks to the Cargo API of the Love and Deepspace wiki (wiki.gg).
"""
import html
import json
import re
import time
from pathlib import Path

import requests

API_URL = "https://loveanddeepspace.wiki.gg/api.php"
HEADERS = {
    # A descriptive User-Agent is polite and helps the wiki admins reach you.
    "User-Agent": "lads-data/0.1 (https://github.com/dareart03/lads-data)"
}

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "tools" / "cache"
RAW_DIR = CACHE_DIR / "raw"

PAGE_SIZE = 500        # rows per request
REQUEST_DELAY = 0.5    # seconds between requests (be nice to the wiki)
MAX_RETRIES = 4


class WikiError(RuntimeError):
    """The wiki API answered with an error."""


def _get(session, params):
    """GET with retries on rate limits and server errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        response = session.get(API_URL, params=params, headers=HEADERS, timeout=60)
        if response.status_code in (429, 500, 502, 503, 504):
            wait = 2 ** attempt
            print(f"  HTTP {response.status_code}, retrying in {wait}s "
                  f"({attempt}/{MAX_RETRIES})")
            time.sleep(wait)
            continue
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise WikiError(f"{data['error'].get('code')}: {data['error'].get('info')}")
        return data
    raise WikiError(f"Gave up after {MAX_RETRIES} attempts")


def cargo_query(table, fields, where=None, order_by="_pageName,_ID"):
    """Download ALL rows of a Cargo table (pages through the results).

    Returns a list of dicts, one per row, keyed by the field names.
    """
    rows = []
    offset = 0
    with requests.Session() as session:
        while True:
            params = {
                "action": "cargoquery",
                "format": "json",
                "tables": table,
                "fields": ",".join(fields),
                "order_by": order_by,
                "limit": PAGE_SIZE,
                "offset": offset,
            }
            if where:
                params["where"] = where
            data = _get(session, params)
            batch = [item["title"] for item in data.get("cargoquery", [])]
            rows.extend(batch)
            print(f"  {table}: {len(rows)} rows")
            if len(batch) < PAGE_SIZE:
                return rows
            offset += PAGE_SIZE
            time.sleep(REQUEST_DELAY)


def parse_page_html(title):
    """Return the rendered HTML of one wiki page (action=parse)."""
    with requests.Session() as session:
        data = _get(session, {
            "action": "parse",
            "page": title,
            "prop": "text",
            "redirects": 1,
            "format": "json",
            "formatversion": 2,
        })
    return data["parse"]["text"]


# An unfilled wiki template parameter is stored literally, e.g. {{{Related Memories}}}
PLACEHOLDER = re.compile(r"^\{\{\{.*\}\}\}$")


def clean(value):
    """Cargo returns HTML-escaped text (e.g. &#039;). Turn it back into text.

    Unfilled template placeholders like {{{Related Memories}}} become "".
    """
    if not isinstance(value, str):
        return value
    text = html.unescape(value).strip()
    return "" if PLACEHOLDER.match(text) else text


def split_list(value):
    """Cargo list fields use ';;' as the delimiter. Empty parts are dropped."""
    if not value:
        return []
    parts = [clean(part) for part in value.split(";;")]
    return [part for part in parts if part]


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)
