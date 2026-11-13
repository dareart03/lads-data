"""Step 6: download card icons and portraits from wiki.gg and save them as WebP.

For every memory with icon base B (memory['icon'] with spaces -> underscores)
the wiki has two files:
    File:{B}_icon.png     the 256x256 square icon
    File:{B}_middle.png   the 248x456 card portrait
They become:
    images/cards/{B}_icon.webp
    images/portraits/{B}_portrait.webp

The wiki renders resized versions on demand (iiurlwidth/iiurlheight), so we
ask for exactly the size we want; the download is converted to WebP locally.

Existing files are skipped unless --refresh is given. At the end the script
lists every card whose wiki file is missing (check for typos in 'icon' or
art that has not been uploaded yet).

Input : data/generated/memories.json
Output: images/cards/*.webp, images/portraits/*.webp

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

from common import API_URL, HEADERS, REPO_ROOT, REQUEST_DELAY, _get, load_json

MEMORIES_FILE = REPO_ROOT / "data" / "generated" / "memories.json"
CARDS_DIR = REPO_ROOT / "images" / "cards"
PORTRAITS_DIR = REPO_ROOT / "images" / "portraits"

# kind -> (wiki file suffix, target size, output dir, output suffix)
KINDS = {
    "icon": ("_icon.png", (256, 256), CARDS_DIR, "_icon.webp"),
    "portrait": ("_middle.png", (248, 456), PORTRAITS_DIR, "_portrait.webp"),
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


def main():
    refresh = "--refresh" in sys.argv
    memories = load_json(MEMORIES_FILE)
    if memories is None:
        raise SystemExit("data/generated/memories.json not found. "
                         "Run update_memories.py first.")
    bases = list(dict.fromkeys(
        (m.get("icon") or "").replace(" ", "_") for m in memories if m.get("icon")))

    problems, done, skipped = [], 0, 0
    with requests.Session() as session:
        for kind, (wiki_suffix, (width, height), out_dir, out_suffix) in KINDS.items():
            titles = {f"File:{base}{wiki_suffix}": base for base in bases}
            todo = {t: b for t, b in titles.items()
                    if refresh or not (out_dir / f"{b}{out_suffix}").exists()}
            skipped += len(titles) - len(todo)
            print(f"{kind}: {len(todo)} to download "
                  f"({len(titles) - len(todo)} already exist)")

            items = sorted(todo.items())
            for offset in range(0, len(items), BATCH):
                batch = items[offset:offset + BATCH]
                found = image_info(session, [t for t, _ in batch], width, height)
                time.sleep(REQUEST_DELAY)
                for title, base in batch:
                    info = found.get(title)
                    if info is None:
                        problems.append(f"{base}: {title} not on the wiki")
                        continue
                    url, _mime = info
                    try:
                        response = session.get(url, headers=HEADERS, timeout=60)
                        response.raise_for_status()
                        save_webp(response.content, out_dir / f"{base}{out_suffix}")
                        done += 1
                    except Exception as error:  # network or PIL failure
                        problems.append(f"{base}: {error}")
                print(f"  {kind}: {min(offset + BATCH, len(items))}/{len(items)}")

    print(f"\nDownloaded {done}, skipped {skipped} existing, "
          f"{len(problems)} problem(s)")
    if problems:
        print("Missing or failed:")
        for line in problems[:30]:
            print("  -", line)
        if len(problems) > 30:
            print(f"  ... and {len(problems) - 30} more")
        sys.exit(1)


if __name__ == "__main__":
    main()
