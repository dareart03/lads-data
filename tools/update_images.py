"""Step 6: download card icons, card portraits, event banners and item icons.

Cards (from data/generated/memories.json, icon base B = memory['icon'] with
spaces -> underscores):
    File:{B}_icon.png     the 256x256 square icon  -> images/cards/{B}_icon.webp
    File:{B}_large.jpg    the card art, up to 1080x1440 -> images/portraits/{B}_portrait.webp
                          (WebP q75; when the wiki has no _large.jpg the
                          248x456 File:{B}_middle.png is used instead)

Events (from data/generated/events.json, base = event_banner_base(name)):
    File:{base}_banner.png  the 826x280 banner    -> images/events/{base}_banner.webp

Item icons (from data/static/icons.json, key -> wiki file name):
    File:{wiki name}                                -> images/icons/{key}.webp
    Rarity stars, position (lunar/solar), stellactrum markers, talent icons,
    currencies, ascension crystals, EXP bottles and awakening hearts - a
    static, hand-curated list (the wiki has no machine-readable item table
    with icons). Originals are downloaded as-is: they are already small.

The wiki renders resized versions on demand (iiurlwidth/iiurlheight), so we
ask for exactly the size we want; the download is converted to WebP locally
(portraits q75, cards/banners q90). Item icons skip the resize and take the
original file.

Existing files are skipped unless --refresh is given. Missing card art and
missing item icons are fatal (the app cannot live without them); a missing
event banner is not - those events simply publish with an empty "image" field.

Input : data/generated/memories.json, data/generated/events.json,
        data/static/icons.json
Output: images/cards/*.webp, images/portraits/*.webp, images/events/*.webp,
        images/icons/*.webp

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
ICONS_FILE = REPO_ROOT / "data" / "static" / "icons.json"
CARDS_DIR = REPO_ROOT / "images" / "cards"
PORTRAITS_DIR = REPO_ROOT / "images" / "portraits"
EVENTS_DIR = REPO_ROOT / "images" / "events"
ICONS_DIR = REPO_ROOT / "images" / "icons"

# kind -> (wiki file suffix, target size, output dir, output suffix, source,
#          webp quality, fallback suffix when the wiki file is missing)
KINDS = {
    "icon": ("_icon.png", (256, 256), CARDS_DIR, "_icon.webp", "memories", 90, None),
    "portrait": ("_large.jpg", (1080, 1440), PORTRAITS_DIR, "_portrait.webp",
                 "memories", 75, "_middle.png"),
    "event": ("_banner.png", (826, 280), EVENTS_DIR, "_banner.webp", "events", 90, None),
}

# size to request for the small card portrait when a memory has no _large.jpg
PORTRAIT_FALLBACK_SIZE = (248, 456)

BATCH = 50   # titles per imageinfo request


def image_info(session, titles, width=None, height=None):
    """imageinfo for up to BATCH titles; returns {title: (url, mime)}.

    The url is the wiki-rendered thumbnail; when no size is given (item
    icons) or the wiki returns none (original smaller than requested) the
    original file url is used.
    """
    params = {
        "action": "query", "format": "json",
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url|mime",
    }
    if width and height:
        params["iiurlwidth"] = width
        params["iiurlheight"] = height
    data = _get(session, params)
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


def save_webp(content, target, quality=90):
    """Convert downloaded image bytes to WebP (alpha is preserved)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(BytesIO(content))
    if image.mode in ("P", "LA", "PA"):
        image = image.convert("RGBA")
    elif image.mode not in ("RGB", "RGBA", "L"):
        image = image.convert("RGB")
    image.save(target, "WEBP", quality=quality, method=6)


def base_of(source, record):
    if source == "memories":
        return (record.get("icon") or "").replace(" ", "_")
    return event_banner_base(record.get("name", ""))


def wanted_files():
    """{kind: [(wiki title, base name)]} for every image the sources name."""
    wanted = {}
    for kind, (suffix, _size, _out_dir, _out_suffix, source,
               _quality, _fallback) in KINDS.items():
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


def wanted_icons():
    """[(wiki title, key)] from data/static/icons.json."""
    icons = load_json(ICONS_FILE, default=None)
    if icons is None:
        raise SystemExit("data/static/icons.json not found.")
    return [(f"File:{name}", key) for key, name in sorted(icons.items())]


def download_icons(session, refresh):
    """Item icons from the static manifest; missing ones are fatal."""
    items = wanted_icons()
    todo = [(t, k) for t, k in items
            if refresh or not (ICONS_DIR / f"{k}.webp").exists()]
    print(f"icons: {len(todo)} to download "
          f"({len(items) - len(todo)} already exist)")
    fatal, done = [], 0
    for offset in range(0, len(todo), BATCH):
        batch = todo[offset:offset + BATCH]
        found = image_info(session, [t for t, _ in batch])
        time.sleep(REQUEST_DELAY)
        for title, key in batch:
            info = found.get(title)
            if info is None:
                fatal.append(f"{key}: {title} not on the wiki")
                continue
            url, _mime = info
            try:
                response = session.get(url, headers=HEADERS, timeout=60)
                response.raise_for_status()
                save_webp(response.content, ICONS_DIR / f"{key}.webp")
                done += 1
            except Exception as error:  # network or PIL failure
                fatal.append(f"{key}: {error}")
        print(f"  icons: {min(offset + BATCH, len(todo))}/{len(todo)}")
    return fatal, done


def main():
    refresh = "--refresh" in sys.argv
    wanted = wanted_files()

    fatal, soft, done, skipped = [], [], 0, 0
    with requests.Session() as session:
        icon_fatal, icon_done = download_icons(session, refresh)
        fatal += icon_fatal
        done += icon_done

        for kind, (suffix, (width, height), out_dir, out_suffix, _src,
                   quality, fallback) in KINDS.items():
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
                    if info is None and fallback:
                        fb_title = f"File:{base}{fallback}"
                        fb = image_info(session, [fb_title],
                                        *PORTRAIT_FALLBACK_SIZE)
                        time.sleep(REQUEST_DELAY)
                        info = fb.get(fb_title)
                        if info is not None:
                            print(f"  {base}: no {suffix} on the wiki, "
                                  f"using {fallback}")
                    if info is None:
                        line = f"{base}: {title} not on the wiki"
                        (soft if kind == "event" else fatal).append(line)
                        continue
                    url, _mime = info
                    try:
                        response = session.get(url, headers=HEADERS, timeout=60)
                        response.raise_for_status()
                        save_webp(response.content,
                                  out_dir / f"{base}{out_suffix}", quality)
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
        print("Missing or failed card art / item icons:")
        for line in fatal[:30]:
            print("  -", line)
        if len(fatal) > 30:
            print(f"  ... and {len(fatal) - 30} more")
        sys.exit(1)


if __name__ == "__main__":
    main()
