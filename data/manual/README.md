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

## achievements_additions.json
Achievements the wiki page does not list (yet). The key is the exact title.
`category` is one of Progress, Training, Home, Spare Time, Kitty Cards, Plushies.
Rewards can be written as a text `reward` ("Diamond|20, Title: Lucky Paw") or,
like the wiki data, as a `rewards` list.

    { "Some Achievement": { "description": "Do something.", "category": "Spare Time",
      "hidden": false, "reward": "Diamond|20" } }

When the wiki gets the achievement, the merge report asks you to delete the entry.

## achievements_overrides.json
Corrections to an achievement the wiki already lists. A field here replaces the
wiki value. The title itself cannot be changed here; use an alias.

    { "Some Achievement": { "description": "Corrected text." } }

## achievement_aliases.json
Older titles of an achievement. Achievement ids are made from the title, so the
app recomputes the old ids from these and keeps completed achievements.

    { "Main Story Clear VIII": ["Under Deepspace Clear VIII / Clear VIII"] }
