"""Step 3c: turn the raw wiki.gg Events table into data/generated/events.json.

Reads the same raw table as update_banners.py but keeps everything that is
NOT a wish pool: login events, promise events, sales, mini events, ....
Wish pools are published separately as banners.json.

Input : tools/cache/raw/Events.json       (made by fetch_raw.py)
        data/generated/memories.json      (optional, cross-check memory names)
Output: data/generated/events.json

Usage:
    python tools/fetch_raw.py Events       # refresh the raw data first
    python tools/update_events.py
"""
from collections import Counter

from update_banners import BANNER_TYPES
from common import (REPO_ROOT, RAW_DIR, clean, load_json, name_changes,
                    report_changes, save_json, split_list)

RAW_FILE = RAW_DIR / "Events.json"
MEMORIES_FILE = REPO_ROOT / "data" / "generated" / "memories.json"
OUTPUT_FILE = REPO_ROOT / "data" / "generated" / "events.json"


def event_kind(wiki_type):
    """'10 Days With You Event' -> '10-days-with-you', 'Promise Event Rerun'
    -> 'promise-rerun'. Unknown future types still get a readable kind."""
    kind = clean(wiki_type).lower()
    if kind.endswith(" event"):
        kind = kind[:-len(" event")]
    return kind.replace(" rerun", "-rerun").replace(" ", "-")


def map_row(row):
    wiki_type = clean(row.get("type", ""))
    return {
        "page": clean(row.get("_pageName", "")),
        "name": clean(row.get("name", "")),
        "kind": event_kind(wiki_type),
        "wikiType": wiki_type,
        "startDate": clean(row.get("startDate", "")),
        "endDate": clean(row.get("endDate", "")),
        "timeReference": clean(row.get("timeReference", "")),
        "tags": split_list(row.get("tags")),
        "series": clean(row.get("series", "")),
        "featured": clean(row.get("featured", "")) == "1",
        "relatedCharacters": split_list(row.get("relatedCharacters")),
        "relatedMemories": split_list(row.get("relatedMemories")),
    }


def check(event, known_memories):
    problems = []
    if not event["name"]:
        problems.append("empty name")
    if event["startDate"] and event["endDate"] and event["endDate"] <= event["startDate"]:
        problems.append("end date is not after start date")
    if (event["startDate"] or event["endDate"]) and not event["timeReference"]:
        problems.append("dates without timeReference")
    if known_memories:
        for memory in event["relatedMemories"]:
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

    events, warnings, seen = [], [], set()
    for row in rows:
        if clean(row.get("type", "")) in BANNER_TYPES:
            continue                      # wish pools are banners, not events
        event = map_row(row)
        for problem in check(event, known_memories):
            warnings.append(f"{event['name'] or event['page']}: {problem}")
        # recurring events (Hunting Season, Illusio, ...) repeat under one
        # name with a different period each time: only the same name AND
        # start date is a real duplicate
        key = (event["name"], event["startDate"])
        if key in seen:
            warnings.append(f"{event['name']}: duplicate (same name and start date)")
            continue
        seen.add(key)
        events.append(event)

    # newest first; events without dates go to the end
    events.sort(key=lambda e: (e["startDate"] != "", e["startDate"]), reverse=True)
    previous = load_json(OUTPUT_FILE, default=[]) or []
    added, vanished = name_changes(previous, events, "name")
    report_changes(added, vanished, "events")
    save_json(OUTPUT_FILE, events)

    print(f"Read {len(rows)} events, kept {len(events)} -> {OUTPUT_FILE}")
    print("By kind:", dict(Counter(e["kind"] for e in events)))
    print("timeReference:", dict(Counter(e["timeReference"] or "(empty)" for e in events)))
    dated = [e["startDate"] for e in events if e["startDate"]]
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
