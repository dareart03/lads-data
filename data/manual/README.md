# Manual data

Files in this folder are edited by hand (or through pull requests).
The scripts never change them. They only report entries that are no longer
needed. JSON has no comments, so the formats are explained here.

Keys are the **exact** names used on the wiki (`Character: Title` for cards).

## memories_overrides.json
Corrections to a card the wiki already has. Any field listed here replaces the
wiki value.

    { "Caleb: His Gravity": { "stellactrumType": "Amber" } }

## memories_additions.json
Cards the wiki does not have yet. `featuredCharacter` is required, everything
else can be filled in later. Base stats go in `data/static/memory_stats.json`.

    { "Xavier: New Card": { "featuredCharacter": "Xavier", "rarity": "5" } }

When the wiki gets the card, the merge report asks you to delete the entry.

## banners_overrides.json
Corrections to a banner the wiki already has, for example a missing list of
featured cards.

    { "Some Banner Rerun (2025)": { "featuredMemories": ["Xavier: Some Card"] } }

## banners_additions.json (optional)
Announced banners the wiki does not have yet. They get `"status": "announced"`.

    { "Future Banner": { "kind": "limited", "startDate": "2026-12-01 05:00:00",
      "endDate": "2026-12-15 04:59:00", "featuredMemories": ["Xavier: Some Card"] } }

## banner_aliases.json (optional)
Older names of a banner, so saved pull records still find it.

    { "Destined Reunion Rerun (2025)": ["Destined Reunion Rerun"] }

## achievements_overrides.json
Fixes for achievements. Key is the achievement `title`. A field replaces the
wiki value, and `prevTitle` names the previous achievement in a chain.
