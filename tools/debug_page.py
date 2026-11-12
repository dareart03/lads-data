"""Show how one wiki page looks to our scripts. Used to fix the stats parser.

Usage (from the repo root):
    python tools/debug_page.py
    python tools/debug_page.py "Zayne: Shattered Simulacrum"
"""
import sys

import requests

from common import API_URL, CACHE_DIR, HEADERS, parse_page_html
from update_stats import html_to_text, parse_stats

title = sys.argv[1] if len(sys.argv) > 1 else "Xavier: Program Fallacy"
print(f"Page: {title}\n")

# 1) the rendered HTML (what update_stats.py reads now)
page = parse_page_html(title)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "page.html").write_text(page, encoding="utf-8")
print(f"HTML: {len(page)} characters (saved to tools/cache/page.html)")
print("Stats found by the parser:", parse_stats(page))

text = html_to_text(page)
for label in ("R0 Level 1", "CRIT Rate"):
    i = text.find(label)
    print(f"\n--- plain text around '{label}' (position {i}) ---")
    if i >= 0:
        print(text[max(0, i - 200): i + 500])

i = page.find("CRIT Rate")
print("\n--- raw HTML around 'CRIT Rate' ---")
print(page[max(0, i - 1500): i + 500] if i >= 0 else "'CRIT Rate' is NOT in the HTML")

# 2) the page source (wikitext), in case the stats are template parameters
response = requests.get(API_URL, headers=HEADERS, timeout=60, params={
    "action": "parse", "page": title, "prop": "wikitext",
    "format": "json", "formatversion": 2})
wikitext = response.json().get("parse", {}).get("wikitext", "")
print(f"\n--- wikitext: {len(wikitext)} characters, first 1800 ---")
print(wikitext[:1800])
