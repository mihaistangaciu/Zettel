#!/usr/bin/env python3
"""Local server: serves the UI and reads the word file from disk on every request.

Usage: python3 server.py [path/to/words.csv] [--port 8000] [--no-header] [--labels German Romanian]
"""
import argparse
import csv
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent


def load_cards(path: Path, header: bool, labels: list) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    # Tab beats semicolon beats comma, checked over the whole file (phrases often contain commas).
    delimiter = "\t" if "\t" in text else ";" if ";" in text else ","
    rows = [r for r in csv.reader(text.splitlines(), delimiter=delimiter) if any(c.strip() for c in r)]
    if header and rows:
        head, *rows = rows
        labels = [(head + ["", ""])[0].strip() or labels[0], (head + ["", ""])[1].strip() or labels[1]]
    cards, skipped = [], 0
    for r in rows:
        a, b = ((r + ["", ""])[0]).strip(), ((r + ["", ""])[1]).strip()
        if a and b:
            cards.append({"a": a, "b": b})
        else:
            skipped += 1  # untranslated phrase
    if not cards:
        raise ValueError("No rows with both columns filled in were found.")
    return {"labels": labels, "cards": cards, "skipped": skipped}


def make_handler(words_path: Path, header: bool = True, labels: list = ("Column 1", "Column 2")):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/cards":
                try:
                    body, status = json.dumps(load_cards(words_path, header, list(labels))).encode(), 200
                except Exception as e:  # shown to the user in the UI
                    body, status = json.dumps({"error": f"{words_path}: {e}"}).encode(), 500
                self._send(status, body, "application/json; charset=utf-8")
            else:
                self._send(404, b"Not found", "text/plain")

        def log_message(self, *args):
            pass

    return Handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=str(ROOT / "words.csv"))
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-header", action="store_true", help="first row is data, not a header")
    ap.add_argument("--labels", nargs=2, default=["German", "Romanian"], metavar=("COL1", "COL2"),
                    help="column names when there is no header row (default: German Romanian)")
    args = ap.parse_args()
    words = Path(args.file).expanduser().resolve()
    url = f"http://127.0.0.1:{args.port}"
    print(f"Words file: {words}\nOpen {url}  (Ctrl+C to stop)")
    webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(words, not args.no_header, args.labels)).serve_forever()
