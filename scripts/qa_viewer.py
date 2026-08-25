#!/usr/bin/env python3
"""Vale of Eternity — Card-Text QA Viewer

Human QA pass: cycle through all 70 cards, art next to the index.json
fields, correct anything that's wrong, save straight back to
cards/index.json. Originated as a throwaway for wayfinder ticket #12 —
the final human-eyes gate before cards/index.json counts as a source
of truth (an earlier automated recheck on #6 mis-called Leviathan's
family; only a direct human look caught it) — kept afterward since
future card-data passes need the same tool.

No framework, no build step, stdlib only.

Usage:
    python3 scripts/qa_viewer.py [--port 9123]
    then open http://localhost:9123 in a browser (WSL2 forwards
    localhost to Windows automatically).

Every save writes the full cards list back to cards/index.json
immediately (pretty-printed, same shape). A one-time backup is taken
on first write as cards/index.json.bak.

Reads cards/index.json fresh from disk on every request rather than
holding an in-memory copy for the life of the process — otherwise an
external edit to the file (another tool, a direct fix) made while this
server sits open in a browser tab would get silently clobbered the
next time a save fires from that stale in-memory state.
"""

import argparse
import json
import os
import sys
import html
import http.server
import socketserver
import urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
INDEX_PATH = os.path.join(ROOT, "cards", "index.json")
BACKUP_PATH = INDEX_PATH + ".bak"
FAMILY_DIR = {"fire": "Fire", "water": "Water", "earth": "Earth", "wind": "Wind", "dragon": "Dragon"}
FAMILIES = list(FAMILY_DIR.keys())

_backed_up = os.path.exists(BACKUP_PATH)


def load_data():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def art_path(card):
    fam_dir = FAMILY_DIR.get(card["family"], card["family"])
    return os.path.join(ROOT, "cards", fam_dir, card["name"] + ".png")


def save_index(data):
    global _backed_up
    if not _backed_up:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            backup_bytes = f.read()
        with open(BACKUP_PATH, "w", encoding="utf-8") as f:
            f.write(backup_bytes)
        _backed_up = True
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def render_page(cards, i):
    i = max(0, min(i, len(cards) - 1))
    card = cards[i]
    art = art_path(card)
    art_exists = os.path.exists(art)
    options = "".join(
        f'<option value="{fam}"{" selected" if fam == card["family"] else ""}>{fam}</option>'
        for fam in FAMILIES
    )
    effects_json = json.dumps(card.get("effects", []), indent=2, ensure_ascii=False)
    flagged = bool(card.get("_qa_flag"))
    flag_count = sum(1 for c in cards if c.get("_qa_flag"))

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>QA {i+1}/{len(cards)} — {html.escape(card['name'])}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #1e1e24; color: #eee; }}
  .row {{ display: flex; gap: 2rem; align-items: flex-start; }}
  .art {{ flex: 0 0 auto; }}
  .art img {{ max-width: 320px; border-radius: 8px; border: 1px solid #444; }}
  .missing {{ width: 320px; height: 440px; border: 2px dashed #a44; display: flex;
              align-items: center; justify-content: center; color: #a44; }}
  .fields {{ flex: 1; display: flex; flex-direction: column; gap: 0.75rem; max-width: 560px; }}
  label {{ font-size: 0.8rem; color: #999; text-transform: uppercase; letter-spacing: 0.04em; }}
  input, select, textarea {{ font: inherit; background: #2a2a33; color: #eee; border: 1px solid #555;
              border-radius: 4px; padding: 0.4rem; width: 100%; box-sizing: border-box; }}
  textarea {{ font-family: ui-monospace, monospace; font-size: 0.85rem; min-height: 160px; }}
  .nav {{ margin-top: 1.5rem; display: flex; gap: 0.75rem; align-items: center; }}
  button {{ font: inherit; padding: 0.5rem 1rem; border-radius: 4px; border: 1px solid #666;
            background: #33333d; color: #eee; cursor: pointer; }}
  button:hover {{ background: #44444f; }}
  button.primary {{ background: #2d5a3a; border-color: #3d7a4f; }}
  .counter {{ color: #999; }}
  .flash {{ color: #7c7; margin-left: 1rem; }}
  form {{ margin: 0; }}
  button.flag {{ background: #5a2d2d; border-color: #7a3d3d; }}
  button.flag.on {{ background: #a44; border-color: #d55; }}
  .flag-banner {{ color: #d55; font-weight: bold; margin-bottom: 0.5rem; }}
</style>
</head>
<body>

<h2>Card {i+1} / {len(cards)} — {html.escape(card['name'])}</h2>
{'<div class="flag-banner">FLAGGED FOR REVIEW</div>' if flagged else ''}

<form method="POST" action="/save">
<input type="hidden" name="index" value="{i}">
<div class="row">
  <div class="art">
    {'<img src="/art/' + str(i) + '">' if art_exists else '<div class="missing">no art file</div>'}
    <div style="font-size:0.75rem;color:#888;margin-top:0.4rem;word-break:break-all;">{html.escape(os.path.relpath(art, ROOT))}</div>
  </div>
  <div class="fields">
    <div>
      <label>Name</label>
      <input name="name" value="{html.escape(card['name'])}">
    </div>
    <div>
      <label>Family</label>
      <select name="family">{options}</select>
    </div>
    <div>
      <label>Cost</label>
      <input name="cost" type="number" value="{card['cost']}">
    </div>
    <div>
      <label>Effects (JSON list of {{type, text}})</label>
      <textarea name="effects">{html.escape(effects_json)}</textarea>
    </div>
  </div>
</div>

<div class="nav">
  <button type="submit" name="go" value="prev" class="primary">&larr; Save &amp; Prev</button>
  <button type="submit" name="go" value="next" class="primary">Save &amp; Next &rarr;</button>
  <button type="submit" name="go" value="stay">Save</button>
  <button type="submit" name="go" value="flag" class="flag{' on' if flagged else ''}">{'Clear flag' if flagged else 'Flag for review'}</button>
  <span class="counter">{i+1} / {len(cards)}</span>
  <span class="counter">({flag_count} flagged)</span>
</div>
</form>

<div style="margin-top:2rem;font-size:0.8rem;color:#777;">
  Every save writes straight to <code>cards/index.json</code> (first save takes a one-time backup at
  <code>cards/index.json.bak</code>). Flags are written as a scratch <code>_qa_flag</code> key —
  strip those before the file is treated as final. Jump to a card:
  <form style="display:inline" method="GET" action="/">
    <input style="width:4rem;display:inline;" type="number" name="i" min="1" max="{len(cards)}" value="{i+1}">
    <button type="submit">Go</button>
  </form>
</div>

</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            qs = urllib.parse.parse_qs(parsed.query)
            i = int(qs.get("i", ["1"])[0]) - 1
            cards = load_data()["cards"]
            body = render_page(cards, i).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path.startswith("/art/"):
            i = int(parsed.path.rsplit("/", 1)[-1])
            cards = load_data()["cards"]
            path = art_path(cards[i])
            if not os.path.exists(path):
                self.send_response(404)
                self.end_headers()
                return
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/save":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        form = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        i = int(form["index"][0])
        data = load_data()
        cards = data["cards"]
        card = cards[i]

        card["name"] = form.get("name", [card["name"]])[0]
        card["family"] = form.get("family", [card["family"]])[0]
        try:
            card["cost"] = int(form.get("cost", [card["cost"]])[0])
        except ValueError:
            pass
        try:
            card["effects"] = json.loads(form.get("effects", ["[]"])[0])
        except json.JSONDecodeError as e:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"Bad effects JSON: {e}\n\nGo back and fix it.".encode("utf-8"))
            return

        go = form.get("go", ["stay"])[0]
        if go == "flag":
            if card.get("_qa_flag"):
                del card["_qa_flag"]
            else:
                card["_qa_flag"] = True

        save_index(data)

        next_i = i
        if go == "next":
            next_i = min(i + 1, len(cards) - 1)
        elif go == "prev":
            next_i = max(i - 1, 0)

        self.send_response(303)
        self.send_header("Location", f"/?i={next_i + 1}")
        self.end_headers()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=9123)
    args = ap.parse_args()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), Handler) as httpd:
        print(f"QA viewer up: http://localhost:{args.port}  (Ctrl+C to stop)")
        print(f"Editing: {INDEX_PATH}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
