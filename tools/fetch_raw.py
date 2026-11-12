"""Step 1: download the raw Cargo tables from wiki.gg into tools/cache/raw/.

Nothing is transformed here. We only want to see what the wiki really returns.

Usage (from the repo root, with the virtual environment active):
    python tools/fetch_raw.py              # Memories and Events
    python tools/fetch_raw.py Memories     # one table only
"""
import sys

from common import RAW_DIR, cargo_query, save_json

# Columns as shown on Special:CargoTables (plus the page name).
TABLES = {
    "Memories": [
        "_pageName", "name", "nameZhHans", "nameZhHant", "nameJa", "nameKo",
        "icon", "rarity", "stellactrum", "position", "buff", "memoryPair",
        "date", "relatedCharacters", "characterNumbers", "sources",
        "sourcesWiki", "description", "releaseDate", "timeReference",
    ],
    "Events": [
        "_pageName", "name", "series", "type", "featured", "tags",
        "relatedCharacters", "relatedCharacterNumbers", "relatedMemories",
        "startDate", "endDate", "timeReference",
    ],
}


def main():
    wanted = sys.argv[1:] or list(TABLES)
    for table in wanted:
        if table not in TABLES:
            sys.exit(f"Unknown table '{table}'. Choose from: {', '.join(TABLES)}")
        print(f"Downloading {table} ...")
        rows = cargo_query(table, TABLES[table])
        out = RAW_DIR / f"{table}.json"
        save_json(out, rows)
        print(f"Saved {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
