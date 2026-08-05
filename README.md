# Vale of Eternity — Local Game Server Assets

Private workspace for building a local Vale of Eternity game server.

## Layout

- `cards/` — card images in family folders (Fire, Water, Earth, Wind, Dragon)
  - filenames are card names (e.g. `cards/Fire/Horned Salamander.png`)
- `scripts/pull_cards.py` — puller: fetches base-game card images from the
  wiki (valeofeternity.wiki.gg) via its MediaWiki API
- `docs/recon_report.md` — asset/licensing recon notes

## Puller

```bash
python3 scripts/pull_cards.py            # all 5 families (70 cards)
python3 scripts/pull_cards.py --dry-run  # preview without downloading
python3 scripts/pull_cards.py --families Fire,Dragon
```

Idempotent — skips files already present.

## Scope

Base game only (70 cards). Artifacts and Curse expansions are optional
rules and deliberately not pulled yet.

## Licensing caution

All card art is © Renegade Game Studios. This repo is for private,
local, non-commercial use only. Do not redistribute.
