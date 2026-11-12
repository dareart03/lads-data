"""Step 2: turn the raw wiki.gg Memories table into data/generated/memories.json.

Input : tools/cache/raw/Memories.json   (made by fetch_raw.py)
Output: data/generated/memories.json

This script only maps wiki data into our own field names. It does NOT apply
manual files or base stats; that happens in the merge step later.

Usage:
    python tools/fetch_raw.py Memories     # refresh the raw data first
    python tools/update_memories.py
"""
import re
from urllib.parse import unquote

from common import REPO_ROOT, RAW_DIR, clean, load_json, save_json, split_list

RAW_FILE = RAW_DIR / "Memories.json"
OUTPUT_FILE = REPO_ROOT / "data" / "generated" / "memories.json"

# Allowed values, used only to print warnings about suspicious rows.
STELLACTRUM = {"Amber", "Emerald", "Pearl", "Ruby", "Sapphire", "Violet"}
POSITIONS = {"Lunar", "Solar"}
RARITIES = {"3", "4", "5"}
BUFFS = {"ATK", "DEF", "HP"}

# Translated names: wiki column -> language tag
NAME_COLUMNS = {
    "nameZhHans": "zh-Hans",
    "nameZhHant": "zh-Hant",
    "nameJa": "ja",
    "nameKo": "ko",
}

# [https://loveanddeepspace.wiki.gg/wiki/Promise_Season_11 Promise Season 11]
EXTERNAL_LINK = re.compile(r"\[https?://[^\s\]]*/wiki/([^\s\]]+)\s+[^\]]*\]")
# [[Promise Season 11]] or [[Promise Season 11|label]]
INTERNAL_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


def extract_source_pages(sources_wiki):
    """Pull the wiki page titles out of the sourcesWiki markup."""
    text = clean(sources_wiki or "")
    pages = []
    for raw in EXTERNAL_LINK.findall(text):
        pages.append(unquote(raw).replace("_", " ").split("#")[0])
    for raw in INTERNAL_LINK.findall(text):
        pages.append(raw.strip().split("#")[0])
    # keep order, drop duplicates
    return list(dict.fromkeys(p for p in pages if p))


def map_row(row):
    characters = split_list(row.get("relatedCharacters"))
    entry = {
        "page": clean(row.get("_pageName", "")),
        "name": clean(row.get("name", "")),
        "featuredCharacter": characters[0] if characters else "",
        "icon": clean(row.get("icon", "")),
        "rarity": clean(row.get("rarity", "")),
        "stellactrumType": clean(row.get("stellactrum", "")),
        "slotType": clean(row.get("position", "")),
        "talent": clean(row.get("buff", "")),
        "releaseDate": clean(row.get("releaseDate", "")),
        "timeReference": clean(row.get("timeReference", "")),
        "sources": split_list(row.get("sources")),
        "sourcePages": extract_source_pages(row.get("sourcesWiki")),
    }
    names = {tag: clean(row[col]) for col, tag in NAME_COLUMNS.items()
             if clean(row.get(col, ""))}
    if names:
        entry["names"] = names
    if clean(row.get("memoryPair", "")):
        entry["memoryPair"] = clean(row["memoryPair"])
    if clean(row.get("description", "")):
        entry["description"] = clean(row["description"])
    return entry, characters


def check(entry, characters):
    """Return a list of human-readable problems for one entry."""
    problems = []
    if not entry["name"]:
        problems.append("empty name")
    if len(characters) != 1:
        problems.append(f"expected 1 character, got {characters}")
    if not entry["icon"]:
        problems.append("no icon")
    if entry["rarity"] not in RARITIES:
        problems.append(f"unexpected rarity '{entry['rarity']}'")
    if entry["stellactrumType"] not in STELLACTRUM:
        problems.append(f"unexpected stellactrum '{entry['stellactrumType']}'")
    if entry["slotType"] not in POSITIONS:
        problems.append(f"unexpected position '{entry['slotType']}'")
    if entry["talent"] not in BUFFS:
        problems.append(f"unexpected buff '{entry['talent']}'")
    if not entry["releaseDate"]:
        problems.append("no release date")
    return problems


def sort_key(entry):
    # newest first, then higher rarity, then character and name
    return (
        entry["releaseDate"] or "",
        entry["rarity"],
        entry["featuredCharacter"],
        entry["name"],
    )


def main():
    rows = load_json(RAW_FILE)
    if rows is None:
        raise SystemExit(f"{RAW_FILE} not found. Run: python tools/fetch_raw.py Memories")

    entries, warnings, seen = [], [], {}
    for row in rows:
        entry, characters = map_row(row)
        for problem in check(entry, characters):
            warnings.append(f"{entry['name'] or entry['page']}: {problem}")
        if entry["name"] in seen:
            warnings.append(f"{entry['name']}: duplicate name (also page "
                            f"'{seen[entry['name']]}')")
            continue
        seen[entry["name"]] = entry["page"]
        entries.append(entry)

    entries.sort(key=sort_key, reverse=True)
    save_json(OUTPUT_FILE, entries)

    print(f"Wrote {len(entries)} memories to {OUTPUT_FILE}")
    refs = {}
    for e in entries:
        refs[e["timeReference"] or "(empty)"] = refs.get(e["timeReference"] or "(empty)", 0) + 1
    print("timeReference values:", refs)
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print("  -", w)
    else:
        print("No warnings.")


if __name__ == "__main__":
    main()
