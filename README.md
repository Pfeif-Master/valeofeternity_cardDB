# Vale of Eternity — Local Game Server Assets

Private workspace for building a local Vale of Eternity game server.

## Layout

- `cards/` — card images in family folders (Fire, Water, Earth, Wind, Dragon)
  - filenames are card names (e.g. `cards/Fire/Horned Salamander.png`)
- `scripts/pull_cards.py` — puller: fetches base-game card images from the
  wiki (valeofeternity.wiki.gg) via its MediaWiki API
- `scripts/qa_viewer.py` — local QA viewer: cycle through all 70 cards next
  to their art for a human pass over `cards/index.json`

## Puller

```bash
python3 scripts/pull_cards.py            # all 5 families (70 cards)
python3 scripts/pull_cards.py --dry-run  # preview without downloading
python3 scripts/pull_cards.py --families Fire,Dragon
```

Idempotent — skips files already present.

## QA viewer

```bash
python3 scripts/qa_viewer.py             # then open http://localhost:9123
```

Shows one card's art next to its `cards/index.json` fields (name, family,
cost, effects) with Prev/Next/Save and a "Flag for review" toggle. Every
save writes straight back to `cards/index.json` (first save takes a backup
at `cards/index.json.bak`); flags are a scratch `_qa_flag` key on the card,
meant to be cleared before the file is treated as final.

## Scope

Base game only (70 cards). Artifacts and Curse expansions are optional
rules and deliberately not pulled yet.

## Licensing caution

All card art is © Renegade Game Studios. non-commercial use only. Do not redistribute card images.
This is a hobby project to practice with AI tools.
