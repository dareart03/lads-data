"""Step 5: read the Achievements page into data/generated/achievements.json.

There is no Cargo table for achievements, so the script reads the rendered
page. Every achievement is a block marked class="lads-filterable" with
data-visibility (true = hidden), data-category and data-characters.

Output: data/generated/achievements.json

Usage:
    python tools/update_achievements.py            # download the page
    python tools/update_achievements.py --cached   # use tools/cache/achievements.html
"""
import hashlib
import html
import re
import sys
from collections import Counter
from datetime import datetime

from common import (CACHE_DIR, REPO_ROOT, load_json, name_changes,
                    parse_page_html, report_changes, save_json)

PAGE_TITLE = "Achievements"
CACHE_FILE = CACHE_DIR / "achievements.html"
OUTPUT_FILE = REPO_ROOT / "data" / "generated" / "achievements.json"

CATEGORIES = {"Progress", "Training", "Kitty Cards", "Plushies", "Spare Time", "Home"}

# the opening tag of one achievement; the attributes can come in any order
BLOCK_TAG = re.compile(r'<div\b[^>]*\bclass="[^"]*\blads-filterable\b[^"]*"[^>]*>')
TITLE = re.compile(r'font-size:\s*1\.15em;">(.*?)</p>', re.S)
DESCRIPTION = re.compile(r'font-weight:\s*500;[^>]*>(.*?)</p>', re.S)
TIPS = re.compile(r'font-weight:\s*600;">\s*Tips\s*</p>\s*<hr[^>]*>\s*<p[^>]*>(.*?)</p>', re.S)
RELEASED = re.compile(r'Released on\s+(.+?)\s*\((UTC[+-]\d+|Server Time)\)')
AMOUNT = re.compile(r'amount-container"><p>([^<]*)</p>')
ITEM_NAME = re.compile(r'class="link-container"><a [^>]*>(.*?)</a>', re.S)
ICON_ALT = re.compile(r'<img alt="([^"]*?)(?: icon)?\.png"')
RARITY = re.compile(r'^[^"]*\b(SSR|SR|R|N)\b')

DATE_FORMATS = ("%Y-%m-%d %H:%M", "%B %d, %Y at %H:%M")


def text_of(fragment):
    """Plain text of an HTML fragment. Block tags become spaces; inline tags
    (links, spans) vanish, so 'Xavier</a>.' stays 'Xavier.'"""
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", fragment)
    text = re.sub(r"(?i)<br\s*/?>|</?(?:p|div|li|tr|td|th)\b[^>]*>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_release(block):
    """('2024-07-15 12:00:00', 'UTC+8') from the 'Released on ...' line."""
    match = RELEASED.search(block)
    if not match:
        return "", ""
    raw, reference = match.group(1).strip(), match.group(2)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d %H:%M:%S"), reference
        except ValueError:
            pass
    return raw, reference          # unknown format: keep the text, the caller warns


def parse_amount(raw):
    raw = raw.replace(",", "").strip()
    return int(raw) if raw.isdigit() else (raw or 1)


def parse_rewards(block):
    start = block.find(">Rewards<")
    if start < 0:
        return []
    ends = [i for i in (block.find(">Tips<", start), block.find("Released on", start)) if i > 0]
    segment = block[start: min(ends)] if ends else block[start:]
    rewards = []
    for chunk in segment.split('class="lads-itemDisplay-container')[1:]:
        name = ITEM_NAME.search(chunk)
        if name:
            name = text_of(name.group(1))
        else:
            icon = ICON_ALT.search(chunk)
            name = icon.group(1) if icon else ""
        amount = AMOUNT.search(chunk)
        rarity = RARITY.match(chunk)
        rewards.append({
            "name": name,
            "amount": parse_amount(amount.group(1)) if amount else 1,
            "rarity": rarity.group(1) if rarity else "",
        })
    return rewards


def attribute(tag, name):
    found = re.search(rf'\b{name}="([^"]*)"', tag)
    return html.unescape(found.group(1)) if found else ""


def parse_page(page):
    starts = list(BLOCK_TAG.finditer(page))
    achievements, warnings = [], []
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(page)
        block = page[match.start(): end]
        title_match, desc_match = TITLE.search(block), DESCRIPTION.search(block)
        title = text_of(title_match.group(1)) if title_match else ""
        date, reference = parse_release(block)
        tips = TIPS.search(block)
        tag = match.group(0)
        characters = [c for c in re.split(r"\s*(?:;;|,)\s*", attribute(tag, "data-characters")) if c]

        entry = {
            "id": hashlib.md5(title.encode()).hexdigest()[:8],
            "title": title,
            "description": text_of(desc_match.group(1)) if desc_match else "",
            "category": attribute(tag, "data-category"),
            "hidden": attribute(tag, "data-visibility") == "true",
            "characters": characters,
            "rewards": parse_rewards(block),
            "releaseDate": date,
            "timeReference": reference,
        }
        if tips and text_of(tips.group(1)):
            entry["tips"] = text_of(tips.group(1))

        label = title or f"block #{i + 1}"
        if not title:
            warnings.append(f"{label}: no title")
        if not entry["description"]:
            warnings.append(f"{label}: no description")
        if not entry["rewards"]:
            warnings.append(f"{label}: no rewards")
        if entry["category"] not in CATEGORIES:
            warnings.append(f"{label}: unexpected category '{entry['category']}'")
        if not reference:
            warnings.append(f"{label}: no release date found")
        elif not re.match(r"\d{4}-\d\d-\d\d ", date):
            warnings.append(f"{label}: unknown date format '{date}'")
        achievements.append(entry)
    return achievements, warnings


def main():
    if "--cached" in sys.argv:
        page = CACHE_FILE.read_text(encoding="utf-8")
        print(f"Using {CACHE_FILE}")
    else:
        print("Downloading the Achievements page ...")
        page = parse_page_html(PAGE_TITLE)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(page, encoding="utf-8")

    achievements, warnings = parse_page(page)
    expected = page.count('lads-filterable"')
    if expected != len(achievements):
        warnings.append(f"page has {expected} 'lads-filterable' marks but {len(achievements)} achievements were read")

    titles = Counter(a["title"] for a in achievements)
    warnings += [f"{t}: duplicate title ({n} times)" for t, n in titles.items() if n > 1]

    previous = load_json(OUTPUT_FILE, default=[]) or []
    added, vanished = name_changes(previous, achievements, "title")
    report_changes(added, vanished, "achievement titles")

    save_json(OUTPUT_FILE, achievements)
    print(f"Wrote {len(achievements)} achievements to {OUTPUT_FILE}")
    print("By category:", dict(Counter(a["category"] for a in achievements)))
    print("Hidden:", sum(a["hidden"] for a in achievements))
    print("Time references:", dict(Counter(a["timeReference"] or "(none)" for a in achievements)))
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings[:30]:
            print("  -", w)
        if len(warnings) > 30:
            print(f"  ... and {len(warnings) - 30} more")
    else:
        print("No warnings.")


if __name__ == "__main__":
    main()
