"""Step 3b: fill in base stats from each card's own wiki page.

The Cargo table has no stats, but every card page shows them (the first tab,
"R0 Level 1"). For every card that has no stats in data/static/memory_stats.json
yet, this script opens the card page, reads HP, ATK, DEF, CRIT Rate and
CRIT DMG, and saves them to data/generated/memory_stats.json.

It is incremental: cards already in the generated file are not downloaded again
(use --refresh to download them all again).

Input : data/generated/memories.json, data/static/memory_stats.json
Output: data/generated/memory_stats.json

Usage:
    python tools/update_stats.py
    python tools/update_stats.py --refresh
"""
import html
import re
import sys
import time

from common import (REPO_ROOT, REQUEST_DELAY, WikiError, load_json,
                    parse_page_html, save_json)

MEMORIES_FILE = REPO_ROOT / "data" / "generated" / "memories.json"
STATIC_STATS = REPO_ROOT / "data" / "static" / "memory_stats.json"
OUTPUT_FILE = REPO_ROOT / "data" / "generated" / "memory_stats.json"

NUMBER = r"([\d,]+(?:\.\d+)?)"
BUFF = r"(?:\s*\(\s*Buff\s*\))?"   # the boosted stat is labelled e.g. "DEF ( Buff )" once tags are stripped
# Page text looks like: HP 2400 ATK 120 DEF (Buff) 66 CRIT Rate 2.6% CRIT DMG 0.0% ...
STATS_PATTERN = re.compile(
    rf"HP{BUFF}\s+{NUMBER}\s+ATK{BUFF}\s+{NUMBER}\s+DEF{BUFF}\s+{NUMBER}\s+"
    rf"CRIT Rate\s+{NUMBER}\s*%\s+CRIT DMG\s+{NUMBER}\s*%"
)


def html_to_text(page_html):
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", page_html)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text)


def number(value):
    """'2,400' -> '2400', '2.6' -> '2.6', '0.0' -> '0' (same style as the old data)."""
    f = float(value.replace(",", ""))
    return str(int(f)) if f.is_integer() else str(f)


def parse_stats(page_html):
    """Level 1 stats of a card page, or None if the page shows none.

    The first match is the first tab (R0 Level 1); the awakened tab comes later.
    """
    match = STATS_PATTERN.search(html_to_text(page_html))
    if not match:
        return None
    hp, atk, defense, crit_rate, crit_damage = (number(v) for v in match.groups())
    return {"baseHp": hp, "baseAtk": atk, "baseDef": defense,
            "baseCritRate": crit_rate, "baseCritDamage": crit_damage}


def main():
    refresh = "--refresh" in sys.argv
    memories = load_json(MEMORIES_FILE)
    if memories is None:
        raise SystemExit("data/generated/memories.json not found. "
                         "Run update_memories.py first.")
    static = load_json(STATIC_STATS, default={})
    old = load_json(OUTPUT_FILE, default={})

    pages = {m["name"]: m["page"] for m in memories}
    # keep earlier results only for cards that still exist
    stats = {n: s for n, s in old.items() if n in pages and not refresh}

    todo = [n for n in pages if n not in static and n not in stats]
    print(f"{len(pages)} cards, {len(static)} have hand-checked stats, "
          f"{len(stats)} scraped earlier, {len(todo)} to download.")

    warnings = []
    for i, name in enumerate(todo, 1):
        try:
            found = parse_stats(parse_page_html(pages[name]))
        except WikiError as error:
            warnings.append(f"{name}: {error}")
            continue
        if found is None:
            warnings.append(f"{name}: no stats on its page")
        else:
            stats[name] = found
        print(f"  [{i}/{len(todo)}] {name}: {found or 'no stats'}")
        time.sleep(REQUEST_DELAY)

    save_json(OUTPUT_FILE, dict(sorted(stats.items())))
    print(f"\nSaved {len(stats)} entries to {OUTPUT_FILE}")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print("  -", w)


if __name__ == "__main__":
    main()
