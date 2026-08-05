#!/usr/bin/env python3
"""Vale of Eternity — Base Game Card Image Puller

Pulls the 70 base-game card images from the wiki (valeofeternity.wiki.gg)
into family folders under cards/ (Fire, Water, Earth, Wind, Dragon).

Filenames are the card names (underscore-separated, matching the wiki
page title), e.g. cards/Fire/Horned_Salamander.png

Source of truth: MediaWiki API on the community wiki.
  - family pages expose galleries:  <File.png>|link=<CardName>
  - original-res URLs come from prop=imageinfo

Usage:
    python3 pull_cards.py [--out DIR] [--families Fire,Water] [--dry-run]

Notes:
  - Base game only. Artifacts / Curse expansions are optional rules
    and are intentionally skipped (their gallery entries carry no
    link=CardName mapping on the wiki).
  - Idempotent: skips files already downloaded.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://valeofeternity.wiki.gg/api.php"
UA = "Nym-VoE-Puller/1.0 (personal local research; contact: none)"

FAMILIES = ["Fire", "Water", "Earth", "Wind", "Dragon"]

# Card names that appear in galleries with a link= target; if a gallery
# entry has no link=, fall back to the file stem cleaned of CamelCase
# (kept here for future expansion support).
GALLERY_ENTRY_RE = re.compile(r"^\s*([^|\n]+?)(?:\|link=([^|\n]+?))?\s*$")


def api_get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def get_family_gallery(family: str) -> list[tuple[str, str]]:
    """Return [(wiki_file, card_name)] for a family page's gallery."""
    data = api_get({"action": "parse", "page": family, "prop": "wikitext", "format": "json"})
    wikitext = data["parse"]["wikitext"]["*"]
    entries: list[tuple[str, str]] = []

    # Find <gallery ...> ... </gallery> block(s)
    for m in re.finditer(r"<gallery[^>]*>(.*?)</gallery>", wikitext, re.S):
        for line in m.group(1).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("<"):
                continue
            gm = GALLERY_ENTRY_RE.match(line)
            if not gm:
                continue
            wiki_file = gm.group(1).strip()
            card_name = gm.group(2).strip() if gm.group(2) else None
            if not card_name:
                # Fallback: file stem, spaces from camel case
                stem = os.path.splitext(wiki_file)[0]
                card_name = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
            entries.append((wiki_file, card_name))
    return entries


def resolve_original_url(wiki_file: str) -> str:
    """Resolve the original-resolution URL for a File: page."""
    title = f"File:{wiki_file}"
    data = api_get({
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "format": "json",
    })
    for page in data["query"]["pages"].values():
        ii = page.get("imageinfo")
        if ii:
            return ii[0]["url"]
    raise RuntimeError(f"no imageinfo for {title}")


def safe_card_filename(card_name: str, ext: str) -> str:
    """Card name -> filesystem-safe filename, underscores for spaces."""
    name = card_name.replace("/", "_").replace("\\", "_")
    ext = ext.lstrip(".") if ext else "png"
    return f"{name}.{ext}"


def download(url: str, dest: str, dry_run: bool = False) -> bool:
    if os.path.exists(dest):
        return False  # already have it
    if dry_run:
        print(f"  would download -> {dest}")
        return True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        f.write(resp.read())
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cards"))
    ap.add_argument("--families", default=",".join(FAMILIES), help="comma-separated family names")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.25, help="seconds between API calls (be polite)")
    args = ap.parse_args()

    families = [f.strip() for f in args.families.split(",") if f.strip()]
    out_root = os.path.abspath(args.out)
    os.makedirs(out_root, exist_ok=True)

    total_new = 0
    for family in families:
        fam_dir = os.path.join(out_root, family)
        os.makedirs(fam_dir, exist_ok=True)
        entries = get_family_gallery(family)
        if not entries:
            print(f"[{family}] WARNING: no gallery entries parsed")
            continue
        print(f"[{family}] {len(entries)} cards")
        for wiki_file, card_name in entries:
            try:
                url = resolve_original_url(wiki_file)
            except Exception as e:
                print(f"  !! {wiki_file}: resolve failed: {e}")
                continue
            ext = os.path.splitext(url.split("?")[0])[1] or os.path.splitext(wiki_file)[1]
            dest = os.path.join(fam_dir, safe_card_filename(card_name, ext))
            if download(url, dest, args.dry_run):
                total_new += 1
            time.sleep(args.sleep)

    print(f"\nDone. {total_new} new files. Output: {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
