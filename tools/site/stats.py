#!/usr/bin/env python3
"""Fetch the GitHub numbers for the four Life Dashboard repos into tools/site/stats.json.

The server runs this every hour, then build.py, so the pages show live stars, forks,
contributors and release counts without a script or a request to GitHub in the browser.
build.py reads stats.json when it is there and recent, and builds without the numbers
otherwise. A failed fetch leaves the previous file alone.

Contributors count people: bots and AI coding agents are left out, the developer is in.

Downloads, counted where they cannot be inflated by a page view:
- The Home Assistant integration: downloads of life_dashboard.zip, which HACS fetches on every
  install and update. Once Home Assistant's opt-in analytics list the integration, its count
  of active installations is kept as well.
- The Grafana stack: pulls of the database image. Every stack install and update pulls it, and
  no other setup does (the MCP image, for one, is also used on its own).
GitHub has no API for a package's pulls, so that number comes from the package page; when the
page changes, the number is left out instead of failing the run.

    python3 tools/site/stats.py
"""
import json, os, re, sys, time, urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "stats.json"
REPOS = {
    "android": "owen282000/life-dashboard-companion-app",
    "ios": "owen282000/life-dashboard-companion-app-ios",
    "home-assistant": "owen282000/life-dashboard-ha",
    "grafana": "owen282000/life-dashboard-stack",
}
# Accounts that are not people. GitHub marks most bots as type "Bot"; the AI agents that
# commit as a user account are named here.
NOT_PEOPLE = {"dependabot[bot]", "github-actions[bot]", "renovate[bot]", "claude", "claude[bot]",
              "anthropic-claude", "copilot", "copilot-swe-agent[bot]", "cursoragent", "cursor[bot]",
              "devin-ai-integration[bot]", "codex", "openai-codex", "chatgpt-codex-connector[bot]"}


def fetch(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "owen282000.com-stats"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode(), r.headers.get("Link", "")


def get(path):
    body, link = fetch(f"https://api.github.com/{path}", "application/vnd.github+json")
    return json.loads(body), link


def hacs_downloads(repo):
    rels, _ = get(f"repos/{repo}/releases?per_page=100")
    return sum(a["download_count"] for r in rels for a in r["assets"] if a["name"] == "life_dashboard.zip")


def ha_active_installs():
    try:
        body, _ = fetch("https://analytics.home-assistant.io/custom_integrations.json")
        return json.loads(body).get("life_dashboard", {}).get("total")
    except Exception:
        return None


def image_pulls(repo, image):
    try:
        body, _ = fetch(f"https://github.com/{repo}/pkgs/container/{image}", "text/html")
        m = re.search(r'Total downloads</span>\s*<h3 title="(\d+)"', body)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def releases(repo):
    """The count without paging through them all: one per page, so the last page number is the count."""
    data, link = get(f"repos/{repo}/releases?per_page=1")
    m = re.search(r'[?&]page=(\d+)>; rel="last"', link)
    return int(m.group(1)) if m else len(data)


def main():
    stats, everyone = {}, set()
    for slug, repo in REPOS.items():
        info, _ = get(f"repos/{repo}")
        people, _ = get(f"repos/{repo}/contributors?per_page=100")
        logins = {c["login"] for c in people if c.get("type") == "User" and c["login"].lower() not in NOT_PEOPLE}
        everyone |= logins
        stats[slug] = {"repo": repo, "stars": info["stargazers_count"], "forks": info["forks_count"],
                       "contributors": len(logins), "releases": releases(repo)}
    stats["home-assistant"]["downloads"] = hacs_downloads(REPOS["home-assistant"])
    stats["home-assistant"]["active"] = ha_active_installs()
    stats["grafana"]["downloads"] = image_pulls(REPOS["grafana"], "life-dashboard-db")
    data = {"fetched": int(time.time()), "repos": stats, "contributors": len(everyone),
            "stars": sum(s["stars"] for s in stats.values())}
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, OUT)
    print(f"stats: {data['stars']} stars, {data['contributors']} contributors")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.exit(f"stats: kept the previous stats.json ({e})")
