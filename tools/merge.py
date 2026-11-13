"""Step 4: combine wiki data with our own data into the final files.

Order for memories:  wiki (generated)  ->  additions  ->  base stats  ->  overrides
Order for banners:   wiki (generated)  ->  additions  ->  overrides    ->  aliases
Order for achievements: same as banners (additions, overrides, aliases)

Inputs : data/generated/memories.json, banners.json, achievements.json
         data/generated/memory_stats.json  (from update_stats.py)
         data/static/memory_stats.json
         data/manual/*.json   (all optional)
Output : tools/dist/data/memories.json, banners.json, achievements.json,
         events.json, rotations.json
         (tools/dist/ is not committed; the publish workflow uses it)

The script never edits files in data/manual/. It only REPORTS entries that are
no longer needed (the wiki now has them) or that match nothing (typos).

Usage:
    python tools/merge.py            # long lists are shortened
    python tools/merge.py --full     # print every line of every list
"""
import hashlib
import sys

from update_memories import sort_key
from common import REPO_ROOT, load_json, save_json

GENERATED = REPO_ROOT / "data" / "generated"
STATIC = REPO_ROOT / "data" / "static"
MANUAL = REPO_ROOT / "data" / "manual"
DIST = REPO_ROOT / "tools" / "dist" / "data"

STAT_FIELDS = ["baseHp", "baseAtk", "baseDef", "baseCritRate", "baseCritDamage"]
# Fields the Android app cannot live without (always present, "" if unknown).
REQUIRED_TEXT = ["page", "name", "featuredCharacter", "stellactrumType", "rarity",
                 "slotType", "talent", "releaseDate"] + STAT_FIELDS
# An addition must at least say who the card belongs to.
ADDITION_REQUIRED = ["featuredCharacter"]


def manual(name):
    """Load a manual file; skip documentation keys that start with '_'."""
    data = load_json(MANUAL / name, default={}) or {}
    return {k: v for k, v in data.items() if not k.startswith("_")}


MAX_LINES = 15


def report_section(title, lines):
    if lines:
        print(f"\n{title} ({len(lines)}):")
        shown = lines if "--full" in sys.argv else lines[:MAX_LINES]
        for line in shown:
            print("  -", line)
        if len(shown) < len(lines):
            print(f"  ... and {len(lines) - len(shown)} more (run with --full to list all)")


# ---------------------------------------------------------------- memories
def new_memory(name, fields):
    entry = {"page": name, "name": name, "icon": "", "timeReference": "",
             "sources": [], "sourcePages": []}
    for field in REQUIRED_TEXT:
        entry.setdefault(field, "")
    entry.update(fields)
    entry["page"] = fields.get("page", name)
    entry["name"] = name
    return entry


def merge_memories(report):
    memories = load_json(GENERATED / "memories.json")
    if memories is None:
        raise SystemExit("data/generated/memories.json not found. "
                         "Run fetch_raw.py and update_memories.py first.")
    by_name = {m["name"]: m for m in memories}

    # 1) additions: cards the wiki does not have (yet)
    for name, fields in manual("memories_additions.json").items():
        if name in by_name:
            report["now_on_wiki"].append(f"memories_additions.json: '{name}'")
            continue
        missing = [f for f in ADDITION_REQUIRED if not fields.get(f)]
        if missing:
            report["problems"].append(f"memories_additions.json: '{name}' lacks {missing}")
            continue
        by_name[name] = new_memory(name, fields)
        report["added"].append(name)

    # 2) base stats (the wiki has none)
    # scraped from the wiki by update_stats.py; the hand-checked static file wins
    stats = dict(load_json(GENERATED / "memory_stats.json", default={}))
    stats.update(load_json(STATIC / "memory_stats.json", default={}))
    for name, entry in by_name.items():
        for field in STAT_FIELDS:
            entry.setdefault(field, "")
        if name in stats:
            for field in STAT_FIELDS:
                entry[field] = stats[name].get(field, "")
        else:
            report["no_stats"].append(name)
    for name in stats:
        if name not in by_name:
            report["unused_stats"].append(name)

    # 3) overrides win over everything
    for name, fields in manual("memories_overrides.json").items():
        entry = by_name.get(name)
        if entry is None:
            report["problems"].append(f"memories_overrides.json: no card named '{name}'")
            continue
        for field, value in fields.items():
            if field == "name":
                report["problems"].append(
                    f"memories_overrides.json: '{name}' cannot change 'name' (rename the key instead)")
            elif entry.get(field) == value:
                report["redundant"].append(
                    f"memories_overrides.json: '{name}'.{field} already is '{value}'")
            else:
                entry[field] = value

    # 4) the app needs every required field to be a string
    for entry in by_name.values():
        for field in REQUIRED_TEXT:
            if not isinstance(entry.get(field), str):
                entry[field] = ""

    # 5) the app looks its images up by these file names; update_images.py
    # downloads exactly these files and pack_images.py ships them in images.zip
    for entry in by_name.values():
        base = (entry.get("icon") or "").replace(" ", "_")
        if base:
            entry["iconArt"] = f"{base}_icon.webp"
            entry["portraitArt"] = f"{base}_portrait.webp"
    return sorted(by_name.values(), key=sort_key, reverse=True)


# ----------------------------------------------------------------- banners
def new_banner(name, fields):
    banner = {"page": name, "name": name, "kind": "limited", "wikiType": "",
              "tags": [], "startDate": "", "endDate": "", "timeReference": "",
              "featuredMemories": [], "status": "announced"}
    banner.update(fields)
    banner["name"] = name
    return banner


def merge_banners(report, memory_names):
    banners = load_json(GENERATED / "banners.json")
    if banners is None:
        raise SystemExit("data/generated/banners.json not found. "
                         "Run fetch_raw.py and update_banners.py first.")
    by_name = {b["name"]: b for b in banners}

    for name, fields in manual("banners_additions.json").items():
        if name in by_name:
            report["now_on_wiki"].append(f"banners_additions.json: '{name}'")
            continue
        by_name[name] = new_banner(name, fields)
        report["added"].append(f"banner {name}")

    for name, fields in manual("banners_overrides.json").items():
        banner = by_name.get(name)
        if banner is None:
            report["problems"].append(f"banners_overrides.json: no banner named '{name}'")
            continue
        for field, value in fields.items():
            if banner.get(field) == value:
                report["redundant"].append(
                    f"banners_overrides.json: '{name}'.{field} already has this value")
            else:
                banner[field] = value

    for name, old_names in manual("banner_aliases.json").items():
        if name not in by_name:
            report["problems"].append(f"banner_aliases.json: no banner named '{name}'")
        else:
            by_name[name]["aliases"] = old_names

    no_featured_ok = {"permanent", "special"}
    for banner in by_name.values():
        banner.setdefault("status", "confirmed")
        if not banner["featuredMemories"] and banner["kind"] not in no_featured_ok:
            report["problems"].append(f"banner '{banner['name']}' has no featured memories")
        for memory in banner["featuredMemories"]:
            if memory not in memory_names:
                report["problems"].append(
                    f"banner '{banner['name']}': unknown memory '{memory}'")
    return sorted(by_name.values(),
                  key=lambda b: (b["startDate"] != "", b["startDate"]), reverse=True)


# ------------------------------------------------------------------- events
def new_event(name, fields):
    event = {"page": name, "name": name, "kind": "", "wikiType": "",
             "tags": [], "series": "", "featured": False,
             "startDate": "", "endDate": "", "timeReference": "",
             "relatedCharacters": [], "relatedMemories": []}
    event.update(fields)
    event["name"] = name
    return event


def merge_events(report, memory_names):
    events = load_json(GENERATED / "events.json")
    if events is None:
        raise SystemExit("data/generated/events.json not found. "
                         "Run update_events.py first.")

    # additions: events the wiki does not list (yet)
    wiki_names = {e["name"] for e in events}
    for name, fields in manual("events_additions.json").items():
        if name in wiki_names:
            report["now_on_wiki"].append(f"events_additions.json: '{name}'")
            continue
        events.append(new_event(name, fields))
        report["added"].append(f"event {name}")

    # an override applies to EVERY occurrence of the name (recurring events
    # appear once per period)
    for name, fields in manual("events_overrides.json").items():
        matches = [e for e in events if e["name"] == name]
        if not matches:
            report["problems"].append(f"events_overrides.json: no event named '{name}'")
            continue
        for event in matches:
            for field, value in fields.items():
                if event.get(field) == value:
                    report["redundant"].append(
                        f"events_overrides.json: '{name}'.{field} already has this value")
                else:
                    event[field] = value

    for event in events:
        event.setdefault("status", "confirmed")
        for memory in event["relatedMemories"]:
            if memory not in memory_names:
                report["problems"].append(
                    f"event '{event['name']}': unknown memory '{memory}'")
    return sorted(events,
                  key=lambda e: (e["startDate"] != "", e["startDate"]), reverse=True)


# --------------------------------------------------------------- rotations
def merge_rotations():
    """The weekly farm rotations are a hand-maintained game constant
    (data/static/rotations.json); merge only republishes them."""
    rotations = load_json(STATIC / "rotations.json")
    if rotations is None:
        raise SystemExit("data/static/rotations.json not found.")
    return rotations


# ------------------------------------------------------------ achievements
def achievement_id(title):
    """Same rule the app has always used: first 8 characters of the MD5 of the title."""
    return hashlib.md5(title.encode()).hexdigest()[:8]


def merge_achievements(report):
    achievements = load_json(GENERATED / "achievements.json")
    if achievements is None:
        raise SystemExit("data/generated/achievements.json not found. "
                         "Run update_achievements.py first.")
    by_title = {a["title"]: a for a in achievements}

    # additions: achievements the wiki page does not list (yet)
    added = 0
    for title, fields in manual("achievements_additions.json").items():
        if title in by_title:
            report["now_on_wiki"].append(f"achievements_additions.json: '{title}'")
            continue
        entry = {"id": achievement_id(title), "title": title, "description": "",
                 "category": "", "hidden": False, "characters": [], "rewards": []}
        entry.update(fields)
        entry["title"] = title
        by_title[title] = entry
        added += 1
    if added:
        report["added"].append(f"{added} achievements from achievements_additions.json")

    for title, fields in manual("achievements_overrides.json").items():
        entry = by_title.get(title)
        if entry is None:
            report["problems"].append(f"achievements_overrides.json: no achievement named '{title}'")
            continue
        for field, value in fields.items():
            if field == "title":
                report["problems"].append(
                    f"achievements_overrides.json: '{title}' cannot change 'title' (use an alias)")
            elif entry.get(field) == value:
                report["redundant"].append(
                    f"achievements_overrides.json: '{title}'.{field} already has this value")
            else:
                entry[field] = value

    # aliases: older titles. The app computes the old ids from these (legacyIds)
    # so achievements the player already completed are still recognised.
    for title, old_titles in manual("achievement_aliases.json").items():
        if title not in by_title:
            report["problems"].append(f"achievement_aliases.json: no achievement named '{title}'")
            continue
        by_title[title]["aliases"] = old_titles
        by_title[title]["legacyIds"] = [achievement_id(t) for t in old_titles]

    seen = {}
    for entry in by_title.values():
        for key in [entry["id"]] + entry.get("legacyIds", []):
            if key in seen and seen[key] != entry["title"]:
                report["problems"].append(
                    f"achievement id {key} is used by both '{seen[key]}' and '{entry['title']}'")
            seen[key] = entry["title"]
    return list(by_title.values())


def main():
    report = {k: [] for k in ("added", "now_on_wiki", "redundant", "problems",
                              "no_stats", "unused_stats")}
    memories = merge_memories(report)
    memory_names = {m["name"] for m in memories}
    banners = merge_banners(report, memory_names)
    achievements = merge_achievements(report)
    events = merge_events(report, memory_names)
    rotations = merge_rotations()

    save_json(DIST / "memories.json", memories)
    save_json(DIST / "banners.json", banners)
    save_json(DIST / "achievements.json", achievements)
    save_json(DIST / "events.json", events)
    save_json(DIST / "rotations.json", rotations)
    print(f"Wrote {len(memories)} memories, {len(banners)} banners, "
          f"{len(achievements)} achievements and {len(events)} events to {DIST}")

    report_section("Added from manual files", report["added"])
    report_section("Now on the wiki: delete these from data/manual/", report["now_on_wiki"])
    report_section("Redundant manual values: the wiki already agrees", report["redundant"])
    report_section("PROBLEMS: fix these", report["problems"])
    report_section("Memories without base stats", report["no_stats"])
    report_section("Stats entries that match no card (renamed on the wiki?)",
                   report["unused_stats"])


if __name__ == "__main__":
    main()
