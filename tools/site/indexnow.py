#!/usr/bin/env python3
"""Tell search engines which pages changed, through IndexNow, after a deploy.

Bing, Yandex, Seznam, Naver and the other IndexNow engines share what one of them receives, and
ChatGPT search and Copilot lean on Bing's index. Cloudflare's Crawler Hints also sends IndexNow
signals, but it reports what changes in its cache: the HTML is not cached there, so it reports
images, the favicon and robots.txt, and hardly a page. This sends the pages themselves.

What counts as changed comes from site/sitemap.xml, so the lastmod there has to mean something
(build.py takes it from each page's `updated:` line or "updated" field). A page is sent when its
lastmod differs from the one sent last time, and a page that left the sitemap is sent once so
the engines see it is gone. tools/site/indexnow.json (git-ignored) remembers what was sent.
Without that file, only pages with today's lastmod are sent: IndexNow is for fresh changes, not
for a site's history, which the sitemap already covers.

The key is the file site/<key>.txt that holds its own name. Before sending, the script fetches it
from the live site and stops if it is not there yet, so run it once the new build is live.

    python3 tools/site/indexnow.py            # send what changed since the last run
    python3 tools/site/indexnow.py --dry-run  # only show what it would send, no network
"""
import datetime
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent.parent / "site"
STATE = HERE / "indexnow.json"
HOST = "owen282000.com"
ENDPOINT = "https://api.indexnow.org/indexnow"
UA = "owen282000.com-indexnow"


def find_key():
    """The one IndexNow key in site/: a .txt file whose content is its own name."""
    keys = [f.stem for f in SITE.glob("*.txt")
            if re.fullmatch(r"[A-Za-z0-9-]{8,128}", f.stem) and f.read_text().strip() == f.stem]
    if len(keys) != 1:
        sys.exit(f"indexnow: expected one key file in site/, found {len(keys)}")
    return keys[0]


def sitemap():
    xml = (SITE / "sitemap.xml").read_text()
    return dict(re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", xml))


def changed(pages, sent):
    if sent is None:
        today = datetime.date.today().isoformat()
        return [u for u, d in pages.items() if d == today]
    return [u for u, d in pages.items() if sent.get(u) != d] + [u for u in sent if u not in pages]


def key_is_live(key):
    try:
        req = urllib.request.Request(f"https://{HOST}/{key}.txt", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode().strip() == key
    except (urllib.error.URLError, OSError):
        return False


def submit(key, urls):
    body = json.dumps({"host": HOST, "key": key, "keyLocation": f"https://{HOST}/{key}.txt",
                       "urlList": urls}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "Content-Type": "application/json; charset=utf-8", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main():
    dry = "--dry-run" in sys.argv[1:]
    key = find_key()
    pages = sitemap()
    try:
        sent = json.loads(STATE.read_text())
    except FileNotFoundError:
        sent = None
    urls = changed(pages, sent)
    if not urls:
        print("indexnow: nothing changed")
        if sent is None and not dry:
            STATE.write_text(json.dumps(pages, indent=1) + "\n")
        return
    print("\n".join(urls))
    if dry:
        print(f"indexnow: would send {len(urls)} URLs (dry run, nothing sent)")
        return
    if not key_is_live(key):
        sys.exit(f"indexnow: https://{HOST}/{key}.txt is not live yet, nothing sent")
    # 200 is accepted, 202 is accepted while the engine still checks the key.
    status = submit(key, urls)
    if status not in (200, 202):
        sys.exit(f"indexnow: {ENDPOINT} answered {status}, nothing recorded; the next run tries again")
    STATE.write_text(json.dumps(pages, indent=1) + "\n")
    print(f"indexnow: sent {len(urls)} URLs ({status})")


if __name__ == "__main__":
    main()
