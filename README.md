# LADS Data

Game data for the MemoryTracker app (Love and Deepspace): memories, banners
and achievements, published as static JSON and WebP images.

## Structure

- `data/generated/` is built by scripts from the wiki. Do not edit by hand.
- `data/manual/` holds corrections, additions and announced banners.
  Edit these files (or open a pull request).
- `data/static/` holds fixed game constants.
- `images/` holds resized WebP images.
- `schemas/` holds the JSON Schemas that define a valid record.
- `tools/` holds the Python scripts.

## Pipeline

Run from the repo root, with the virtual environment active
(`pip install -r requirements.txt`):

```
python tools/fetch_raw.py                 # 1. raw wiki tables (Memories, Events)
python tools/update_memories.py           # 2. data/generated/memories.json
python tools/update_banners.py            # 3. data/generated/banners.json
python tools/update_events.py             # 3c. the rest of the Events table
python tools/update_stats.py              # 4. base stats scraped from card pages
python tools/update_achievements.py       # 5. data/generated/achievements.json
python tools/merge.py                     # 6. manual files + stats + schemas of the app
python tools/validate.py                  #    check dist/data against the schemas
python tools/update_images.py             # 7. images/cards + images/portraits (WebP)
python tools/pack_images.py               # 8. images.zip + manifests (fails on missing art)
```

`tools/dist/` is not committed; the publish workflow in GitHub Actions builds
it from scratch and serves it as the app's data API.

The update scripts never touch `data/manual/` (your own data lives there and
survives every run). Each of them also reports which names are new and which
vanished on the wiki since the last run, so a rename or removal is always
visible in the log.

## Published format (tools/dist/)

- `index.json` — `version` (UTC date), `generatedAt`, and entry points:
  `data.memories|banners|achievements` (file + record count) and
  `images` (zip + meta + file count). The app compares `version` to decide
  whether to download an update.
- `data/memories.json` — the array of Memory records (see
  `schemas/memory.schema.json`). `iconArt` and `portraitArt` are file names
  inside `images.zip` (under `cards/` and `portraits/`).
- `data/banners.json`, `data/achievements.json` — same idea, see
  `schemas/banner.schema.json` and `schemas/achievement.schema.json`.
- `data/events.json` — everything in the Events table that is not a wish
  pool (login, promise, sale, mini events, ...), same shape as banners.
  Recurring events (Hunting Season, Illusio, ...) appear once per period,
  so several rows can share a name — match them by `startDate` too.
  Together with `banners.json` it is the dataset for "what is active now /
  what starts next" screens with countdown timers. `startDate`, `endDate`
  and `timeReference` (`UTC+8` / `Server Time`) let the app compute the
  remaining time; `status: "announced"` marks entries without dates yet.
- `data/rotations.json` — the weekly farm rotations (which characters'
  Orbit stages and which protocore colors in Core Hunt are open each day).
  Hand-maintained in `data/static/` — the wiki has no machine-readable
  source; check it against the game when a new love interest is released.
  The app counts the weekday in `timeReference` and looks the day up.
- `images.zip` — WebP images in `cards/` (256×256 icons) and `portraits/`
  (248×456 card art), named after the wiki icon base with spaces replaced by
  underscores, e.g. `cards/Zayne_Shattered_Simulacrum_icon.webp` and
  `portraits/Zayne_Shattered_Simulacrum_portrait.webp`.
- `cards/`, `portraits/` — the same images as loose files. Apps that need
  only a few images can fetch them straight by URL (`cards/<iconArt>`,
  `portraits/<portraitArt>`) instead of unpacking the zip; consumers that
  want everything in one download use `images.zip`.
- `images_meta.json` — `version`, `generatedAt` and a `files` list with
  `path`, `bytes` and `sha256` for integrity checks.

## Attribution

Text data is derived from the Love and Deepspace Wiki
(https://loveanddeepspace.wiki.gg/), licensed under CC BY-SA 4.0.
Game art and names belong to their respective owners.
This is an unofficial fan project.