"""Step 7: pack the WebP images and write the publish manifests.

Scans images/cards/, images/portraits/ and images/events/ and builds, in
tools/dist/:
    images.zip        all images, with cards/, portraits/ and events/ folders
    cards/, portraits/, events/  the same images as loose files, so external
                    apps can fetch one image by URL without unpacking the zip
    images_meta.json  version, date and a size+hash list of every file
    index.json        version, date and record/file counts for everything,
                      so the app can tell whether an update is available

Every memory in dist/data/memories.json must have its iconArt in the pack
(under cards/) and its portraitArt under portraits/; the script exits with
an error when a referenced file is missing, so a broken pack is never
published silently. Events reference their banner through the "image"
field, which is filled here: the file name when the pack has the banner,
"" when the wiki has none. Files on disk that no record uses (e.g. after
a wiki rename) are kept in the pack and only reported.

Usage (from the repo root, after merge.py and update_images.py):
    python tools/pack_images.py
"""
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from common import REPO_ROOT, event_banner_base, load_json, save_json

IMAGES_DIR = REPO_ROOT / "images"
DIST_DIR = REPO_ROOT / "tools" / "dist"
DATA_DIR = DIST_DIR / "data"
FOLDERS = {"cards": IMAGES_DIR / "cards", "portraits": IMAGES_DIR / "portraits",
           "events": IMAGES_DIR / "events"}

MAX_REPORT = 20


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files():
    """{folder: {file name: path}} for every WebP we have on disk."""
    found = {}
    for folder, directory in FOLDERS.items():
        files = {p.name: p for p in sorted(directory.glob("*.webp"))} \
            if directory.exists() else {}
        found[folder] = files
        print(f"{folder}: {len(files)} WebP files")
    return found


def missing_art(found):
    """memories.json references with no file on disk. Fatal: shipping the
    pack would leave the app with broken images."""
    problems = []
    for memory in load_json(DATA_DIR / "memories.json", default=[]):
        name = memory.get("name", "?")
        icon = memory.get("iconArt")
        portrait = memory.get("portraitArt")
        if not icon or not portrait:
            problems.append(f"{name}: no iconArt/portraitArt in memories.json")
            continue
        if icon not in found["cards"]:
            problems.append(f"{name}: {icon} not in images/cards/")
        if portrait not in found["portraits"]:
            problems.append(f"{name}: {portrait} not in images/portraits/")
    return problems


def unused_art(found):
    """Files on disk that no record uses (usually a card renamed on the
    wiki). They stay on disk and in the pack; the pack would only grow
    stale, never broken. Listed so the rename can be checked."""
    memories = load_json(DATA_DIR / "memories.json", default=[])
    events = load_json(DATA_DIR / "events.json", default=[])
    used_icons = {m.get("iconArt") for m in memories}
    used_portraits = {m.get("portraitArt") for m in memories}
    used_banners = {e.get("image") for e in events}
    unused = [f"cards/{f}" for f in found["cards"] if f not in used_icons]
    unused += [f"portraits/{f}" for f in found["portraits"]
               if f not in used_portraits]
    unused += [f"events/{f}" for f in found["events"]
               if f not in used_banners]
    return sorted(unused)


def fill_event_images(found):
    """Set the 'image' field of every event in dist: the banner file name
    when the pack has one, "" when the wiki has no banner (pack_images
    runs after update_images, so disk state is the source of truth)."""
    events_file = DATA_DIR / "events.json"
    events = load_json(events_file, default=[])
    with_banner = 0
    for event in events:
        name = event.get("image") or f"{event_banner_base(event.get('name', ''))}_banner.webp"
        if name in found["events"]:
            event["image"] = name
            with_banner += 1
        else:
            event["image"] = ""
    save_json(events_file, events)
    print(f"events: {with_banner} of {len(events)} have a banner")


def build_zip(found):
    target = DIST_DIR / "images.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_STORED) as archive:
        for folder, files in found.items():
            for name, path in files.items():
                archive.write(path, f"{folder}/{name}")
    return target


def copy_loose(found):
    """The same images as plain files next to the zip: <folder>/<name>.webp.

    External apps can then fetch one image by URL (e.g. cards/X_icon.webp)
    without downloading and unpacking images.zip.
    """
    for folder, files in found.items():
        target_dir = DIST_DIR / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        for name, path in files.items():
            target = target_dir / name
            if not target.exists() or target.stat().st_size != path.stat().st_size:
                target.write_bytes(path.read_bytes())
    print("copied loose images to dist/" + ", dist/".join(found) + "/")


def main():
    now = datetime.now(timezone.utc)
    version = now.date().isoformat()
    found = collect_files()
    fill_event_images(found)

    missing = missing_art(found)
    if missing:
        print(f"\n{len(missing)} problem(s) — not writing the pack:")
        for line in missing[:MAX_REPORT]:
            print("  -", line)
        if len(missing) > MAX_REPORT:
            print(f"  ... and {len(missing) - MAX_REPORT} more")
        sys.exit(1)

    unused = unused_art(found)
    if unused:
        print(f"\n{len(unused)} file(s) no memory uses — kept in the pack "
              f"(the card was probably renamed on the wiki):")
        for line in unused[:MAX_REPORT]:
            print("  -", line)
        if len(unused) > MAX_REPORT:
            print(f"  ... and {len(unused) - MAX_REPORT} more")

    zip_path = build_zip(found)
    print(f"wrote {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    copy_loose(found)

    file_entries = []
    for folder, files in found.items():
        for name, path in files.items():
            file_entries.append({
                "path": f"{folder}/{name}",
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    save_json(DIST_DIR / "images_meta.json", {
        "version": version,
        "generatedAt": now.isoformat(timespec="seconds"),
        "files": file_entries,
    })

    index = {"version": version,
             "generatedAt": now.isoformat(timespec="seconds"), "data": {}}
    for kind in ("memories", "banners", "achievements", "events", "rotations"):
        records = load_json(DATA_DIR / f"{kind}.json", default=[])
        # rotations.json is one document with two schedules, not a list
        count = (len(records.get("orbit", {})) + len(records.get("coreHunt", {}))
                 if isinstance(records, dict) else len(records))
        index["data"][kind] = {"file": f"data/{kind}.json", "count": count}
    index["images"] = {
        "file": "images.zip",
        "meta": "images_meta.json",
        "count": len(file_entries),
        "folders": {"cards": "cards/", "portraits": "portraits/",
                    "events": "events/"},
    }
    save_json(DIST_DIR / "index.json", index)
    print(f"wrote index.json (version {version}) and "
          f"images_meta.json ({len(file_entries)} files)")


if __name__ == "__main__":
    main()
