"""Step 6: download card icons, card portraits and event banners as WebP.

Cards (from data/generated/memories.json, icon base B = memory['icon'] with
spaces -> underscores):
    File:{B}_icon.png     the 256x256 square icon  -> images/cards/{B}_icon.webp
    File:{B}_middle.png   the 248x456 card portrait -> images/portraits/{B}_portrait.webp

Events (from data/generated/events.json, base = event_banner_base(name)):
    File:{base}_banner.png  the 826x280 banner    -> images/events/{base}_banner.webp

The wiki renders resized versions on demand (iiurlwidth/iiurlheight), so we
ask for exactly the size we want; the download is converted to WebP locally.

Existing files are skipped unless --refresh is given. Missing card art is
fatal (the app cannot live without it); a missing event banner is not —
those events simply publish with an empty "image" field.

Input : data/generated/memories.json, data/generated/events.json
Output: images/cards/*.webp, images/portraits/*.webp, images/events/*.webp

Usage (from the repo root):
    python tools/update_images.py
    python tools/update_images.py --refresh
"""
import sys
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

from common import (API_URL, HEADERS, REPO_ROOT, REQUEST_DELAY, _get,
                    event_banner_base, load_json)

MEMORIES_FILE = REPO_ROOT / "data" / "generated" / "memories.json"
EVENTS_FILE = REPO_ROOT / "data" / "generated" / "events.json"
CARDS_DIR = REPO_ROOT / "images" / "cards"
PORTRAITS_DIR = REPO_ROOT / "images" / "portraits"
EVENTS_DIR = REPO_ROOT / "images" / "events"

# kind -> (wiki file suffix, target size, output dir, output suffix, source)
KINDS = {
    "icon": ("_icon.png", (256, 256), CARDS_DIR, "_icon.webp", "memories"),
    "portrait": ("_middle.png", (248, 456), PORTRAITS_DIR, "_portrait.webp", "memories"),
    "event": ("_banner.png", (826, 280), EVENTS_DIR, "_banner.webp", "events"),
}

BATCH = 50   # titles per imageinfo request


def image_info(session, titles, width, height):
    """imageinfo for up to BATCH titles; returns {title: (url, mime)}.

    The url is the wiki-rendered thumbnail; when the wiki returns none
    (original smaller than requested) the original file url is used.
    """
    data = _get(session, {
        "action": "query", "format": "json",
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url|mime", "iiurlwidth": width, "iiurlheight": height,
    })
    found = {}
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo")
        if info:
            # the API answers with spaces in titles even when asked with
            # underscores ("File:A B icon.png"); normalise back to underscores
            found[page["title"].replace(" ", "_")] = (
                info[0].get("thumburl") or info[0]["url"],
                info[0].get("mime", ""))
    return found


def save_webp(content, target):
    """Convert downloaded image bytes to WebP (alpha is preserved)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(BytesIO(content))
    if image.mode in ("P", "LA", "PA"):
        image = image.convert("RGBA")
    elif image.mode not in ("RGB", "RGBA", "L"):
        image = image.convert("RGB")
    image.save(target, "WEBP", quality=90, method=6)


def base_of(source, record):
    if source == "memories":
        return (record.get("icon") or "").replace(" ", "_")
    return event_banner_base(record.get("name", ""))


def wanted_files():
    """{kind: [(wiki title, base name)]} for every image the sources name."""
    wanted = {}
    for kind, (suffix, _size, _out_dir, _out_suffix, source) in KINDS.items():
        source_file = MEMORIES_FILE if source == "memories" else EVENTS_FILE
        records = load_json(source_file, default=[]) or []
        seen, items = set(), []
        for record in records:
            base = base_of(source, record)
            if not base or base in seen:
                continue                      # recurring events share a banner
            seen.add(base)
            items.append((f"File:{base}{suffix}", base))
        wanted[kind] = items
    return wanted


def main():
    refresh = "--refresh" in sys.argv
    wanted = wanted_files()

    fatal, soft, done, skipped = [], [], 0, 0
    with requests.Session() as session:
        for kind, (suffix, (width, height), out_dir, out_suffix, _src) in KINDS.items():
            titles = wanted[kind]
            todo = [(t, b) for t, b in titles
                    if refresh or not (out_dir / f"{b}{out_suffix}").exists()]
            skipped += len(titles) - len(todo)
            print(f"{kind}: {len(todo)} to download "
                  f"({len(titles) - len(todo)} already exist)")

            items = sorted(todo)
            for offset in range(0, len(items), BATCH):
                batch = items[offset:offset + BATCH]
                found = image_info(session, [t for t, _ in batch], width, height)
                time.sleep(REQUEST_DELAY)
                for title, base in batch:
                    info = found.get(title)
                    if info is None:
                        line = f"{base}: {title} not on the wiki"
                        (soft if kind == "event" else fatal).append(line)
                        continue
                    url, _mime = info
                    try:
                        response = session.get(url, headers=HEADERS, timeout=60)
                        response.raise_for_status()
                        save_webp(response.content, out_dir / f"{base}{out_suffix}")
                        done += 1
                    except Exception as error:  # network or PIL failure
                        (soft if kind == "event" else fatal).append(
                            f"{base}: {error}")
                print(f"  {kind}: {min(offset + BATCH, len(items))}/{len(items)}")

    print(f"\nDownloaded {done}, skipped {skipped} existing, "
          f"{len(fatal)} fatal problem(s), {len(soft)} without event banner")
    if soft:
        print(f"{len(soft)} event banner(s) not on the wiki "
              f"(those events publish with an empty 'image'):")
        for line in soft[:20]:
            print("  -", line)
        if len(soft) > 20:
            print(f"  ... and {len(soft) - 20} more")
    if fatal:
        print("Missing or failed card art:")
        for line in fatal[:30]:
            print("  -", line)
        if len(fatal) > 30:
            print(f"  ... and {len(fatal) - 30} more")
        sys.exit(1)


if __name__ == "__main__":
    main()
