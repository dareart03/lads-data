"""Step 3: turn the raw wiki.gg Events table into data/generated/banners.json.

Banners are the wish-pool rows of the Events table. Everything else
(login events, promise events, ...) is ignored.

Input : tools/cache/raw/Events.json       (made by fetch_raw.py)
        data/generated/memories.json      (optional, used to cross-check names)
Output: data/generated/banners.json

Usage:
    python tools/fetch_raw.py Events       # refresh the raw data first
    python tools/update_banners.py
"""
from collections import Counter

from common import REPO_ROOT, RAW_DIR, clean, load_json, save_json, split_list

RAW_FILE = RAW_DIR / "Events.json"
MEMORIES_FILE = REPO_ROOT / "data" / "generated" / "memories.json"
OUTPUT_FILE = REPO_ROOT / "data" / "generated" / "banners.json"

# wiki "type" -> our "kind"
BANNER_TYPES = {
    "Limited Wish Pool": "limited",
    "Limited Wish Pool Rerun": "rerun",
    "Permanent Wish Pool": "permanent",
    "Special Wish Pool": "special",
}

# Special pools have no fixed featured cards (the player picks standard cards).
# These kinds are expected to have an empty featuredMemories list.
NO_FEATURED_EXPECTED = {"permanent", "special"}


def map_row(row):
    wiki_type = clean(row.get("type", ""))
    banner = {
        "page": clean(row.get("_pageName", "")),
        "name": clean(row.get("name", "")),
        "kind": BANNER_TYPES[wiki_type],
        "wikiType": wiki_type,
        "tags": split_list(row.get("tags")),
        "startDate": clean(row.get("startDate", "")),
        "endDate": clean(row.get("endDate", "")),
        "timeReference": clean(row.get("timeReference", "")),
        "featuredMemories": split_list(row.get("relatedMemories")),
    }
    return banner


def check(banner, known_memories):
    problems = []
    if not banner["name"]:
        problems.append("empty name")
    if banner["kind"] != "permanent":
        if not banner["startDate"] or not banner["endDate"]:
            problems.append("missing start or end date")
        elif banner["endDate"] <= banner["startDate"]:
            problems.append("end date is not after start date")
        if not banner["timeReference"]:
            problems.append("no timeReference")
    if not banner["featuredMemories"] and banner["kind"] not in NO_FEATURED_EXPECTED:
        problems.append("no featured memories")
    if known_memories:
        for memory in banner["featuredMemories"]:
            if memory not in known_memories:
                problems.append(f"unknown memory '{memory}'")
    return problems


def main():
    rows = load_json(RAW_FILE)
    if rows is None:
        raise SystemExit(f"{RAW_FILE} not found. Run: python tools/fetch_raw.py Events")

    memories = load_json(MEMORIES_FILE, default=[])
    known_memories = {m["name"] for m in memories}
    if not known_memories:
        print("Note: memories.json not found, skipping the memory-name check.\n")

    banners, warnings, seen = [], [], set()
    for row in rows:
        if clean(row.get("type", "")) not in BANNER_TYPES:
            continue
        banner = map_row(row)
        for problem in check(banner, known_memories):
            warnings.append(f"{banner['name'] or banner['page']}: {problem}")
        if banner["name"] in seen:
            warnings.append(f"{banner['name']}: duplicate banner name")
            continue
        seen.add(banner["name"])
        banners.append(banner)

    # newest first; permanent banners (no dates) go to the end
    banners.sort(key=lambda b: (b["startDate"] != "", b["startDate"]), reverse=True)
    save_json(OUTPUT_FILE, banners)

    print(f"Read {len(rows)} events, kept {len(banners)} banners -> {OUTPUT_FILE}")
    print("By kind:", dict(Counter(b["kind"] for b in banners)))
    print("timeReference:", dict(Counter(b["timeReference"] or "(empty)" for b in banners)))
    dated = [b["startDate"] for b in banners if b["startDate"]]
    if dated:
        print(f"Date range: {min(dated)} .. {max(dated)}")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print("  -", w)
    else:
        print("No warnings.")


if __name__ == "__main__":
    main()
