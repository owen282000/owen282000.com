#!/usr/bin/env python3
"""Build owen282000.com: the developer page, the Life Dashboard site and its guides, in every language.

One source for everything that repeats: the navigation, the footer, the install buttons and
cards, the structured data, the store status text, llms.txt and the sitemap. Run it from
anywhere after changing any page or any data below:

    python3 tools/site/build.py                # build, and list what is still to translate
    python3 tools/site/build.py --strict de    # also fail on anything German still lacks
    python3 tools/site/build.py --strict       # the same for every language

Where the words live: tools/site/i18n/<lang>/ (i18n/README.md is the brief for translators).
- lang.json: the language itself (folder on the site, hreflang, month names, "complete").
- strings.json: everything the templates say (navigation, buttons, footer, the names and
  one-line descriptions of the guides, alt texts, the store sentences).
- guides/<id>.html: a guide. It starts with a comment holding its title and description;
  screenshot placeholders like <!-- IMG: pair dialog (A2-pair.png) --> become figures.
- products/<id>.json: a product page (Android, iPhone, Home Assistant, Grafana, and the two
  dashboard cards: the Screen Time cards and the Sleep Card). Each section shows an "image", or
  a "code" window ({"title", "code"}) instead.
- pages/landing.html, hub.html, privacy.html, ios-privacy.html: the pages written by hand, as
  the inside of <main>. Between the landing page's <!-- BUILD:name --> markers the script fills
  in the shared parts (the store badges, the hero picture, the install section, the guide list,
  the numbers); its FAQPage JSON-LD comes from the questions on the page.
English (i18n/en/) is the source and keeps its addresses: /, /privacy/, /life-dashboard/...
A translation is served under its folder: /de/life-dashboard/android/. This file holds the
structure only (which pages exist, their links, images and structured data), no prose.

What it writes: site/index.html, site/privacy/, site/legal/ (trademark notices, badge credits and
the imprint, from strings.json), site/life-dashboard/ (the landing page, the
products, the guides, the guide index at guides/, ios/privacy/), the same under site/<lang>/
for every page a language has, site/404.html, llms.txt (in site/ and site/life-dashboard/, from
llms.txt.in) and site/sitemap.xml with every page's hreflang alternates. site/life-dashboard/
site.css and img/ are the stylesheet and images themselves, shared by every language.

Every page gets a canonical to itself, hreflang links to each language it exists in (itself
included) and x-default to English, <html lang>, Open Graph and Twitter tags in its language,
and a language menu that leads to the same page in the other languages. Nothing redirects on
the browser's language. check() refuses hreflang that is not mutual, a translated page that
links to an English page although the translation exists, a fragment that leads nowhere, a
title or description used twice and a heading or title that ends with a full stop; for a language marked "complete" (or named with --strict)
also a missing page, a missing string, and a translation whose code, screenshots or tables
differ from the English page.

Store status lives in PARTS_BASE only. Text anywhere can say {{status:android}} or {{status:ios}}
and gets the current sentence ("status" in strings.json), or {{play_url}} for a link to the Play
listing.

Store badges: every route with an entry in BADGE_FILES shows its official badge, saved once in
site/life-dashboard/img/badges/ (never hotlinked, never recolored, cropped or faded). A live
route links its badge; a route that is still "soon" shows the same unaltered badge unlinked,
inside a dashed "Coming soon" frame with its caption from strings.json. Routes without a badge keep
the text links (alt_links). GitHub has no official badge, so the APK stays a plain button.

Launch day for Google Play or the App Store:
1. The official badge is already in img/badges/ (Google's badge page, Apple's Marketing Tools),
   shown as "Coming soon" until now. Never replace it with a recolored or cropped copy.
2. In PARTS_BASE, set that entry's "status" to "live" (check its "href", and its "note" in strings.json).
3. Update "status" in strings.json, run the script. It refuses to build while a page still says the store is
   coming. Live stores then lead every hero and install card with their official badge.
Both are live now: the App Store since October 21, 2026, Google Play since October 27, 2026.
On Android, Google Play leads with its "pitch" (price and why), and the free routes follow under
the part's "free_line". Play links carry a campaign referrer per page and language (PLAY_LINK,
PLACES and emit()), App Store links a campaign token per page and language (APP_STORE_LINK,
app_place() and emit()); in a page's text they are {{play_url}} and {{app_store_url}}.

F-Droid goes live (once https://f-droid.org/packages/com.owen282000.lifedashboard/ answers
instead of a 404): in PARTS_BASE, set the "fdroid" entry's "status" to "live". That one line turns
the framed "Accepted, live with F-Droid's next build" badge into a linked one everywhere, and
the STALE check then refuses any page that still says F-Droid is pending.

Live GitHub numbers: stats.py writes tools/site/stats.json (not in git). With a recent one, the
landing page shows the stars, contributors and Android releases, and every product page its
repo's stars, forks and contributors (the integration and the stack also their downloads, see
stats.py for how they are counted). Without it, the landing page keeps the floors in PROOF_FLOORS
and the product pages show no numbers. The server runs stats.py and this script every hour.
"""
import hashlib, html, json, re, shutil, sys, time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SITE = ROOT / "site"
OUT = SITE / "life-dashboard"
I18N = HERE / "i18n"
DOMAIN = "https://owen282000.com/"
BASE = DOMAIN + "life-dashboard/"
# Every link the templates write is the English address from the root of the site; emit()
# points each one at the page in the language being built (see localize()).
LD = "/life-dashboard/"
UPDATED = "2026-10-06"

# ---------------------------------------------------------------------------------------------
# Languages. i18n/<code>/lang.json describes one language: its folder on the site ("" for
# English, which keeps its addresses), its hreflang, its own name for the language menu, the
# og:locale, month names and the date pattern, and "complete": true once every page is
# translated, from when a missing page or string fails the build.
LANGS = {}
for _f in sorted(I18N.glob("*/lang.json")):
    _m = json.loads(_f.read_text())
    LANGS[_m["code"]] = _m
LANGS = dict(sorted(LANGS.items(), key=lambda kv: kv[1]["order"]))
STRINGS = {c: json.loads((I18N / c / "strings.json").read_text()) for c in LANGS if (I18N / c / "strings.json").exists()}
EN = STRINGS["en"]
L = "en"                 # the language being built, set by activate()
MISSING = {c: set() for c in LANGS}   # strings a language still takes from English


def lookup(d, path):
    for k in path.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def S(path, lang=None):
    """A value from the language's strings.json, by dotted path. A language that lacks it gets
    the English one, and the path is noted for the "still to translate" report."""
    lang = lang or L
    v = lookup(STRINGS.get(lang, {}), path)
    if v is None or v == "":
        if lang != "en":
            MISSING[lang].add(path)
        v = lookup(EN, path)
        if v is None:
            sys.exit(f"strings.json: no such key {path}")
    return v


def t(key, **fmt):
    """A line of the chrome (navigation, buttons, footer): ui.<key> in strings.json."""
    v = S("ui." + key)
    return v.format(**fmt) if fmt else v


def date_text(iso, lang=None):
    """2026-10-12 as October 12, 2026 (or 12. Oktober 2026), for the byline."""
    m = LANGS[lang or L]
    y, mo, d = (int(x) for x in iso.split("-"))
    return m["date"].format(d=d, month=m["months"][mo - 1], y=y)


# The date each page last changed, so a lastmod in the sitemap means something: a page without
# an `updated:` line (guides) or "updated" field (products) keeps UPDATED, the site's launch day.
PAGE_DATES = {}

REPO = "https://github.com/owen282000/life-dashboard-companion-app"
REPO_IOS = "https://github.com/owen282000/life-dashboard-companion-app-ios"
REPO_HA = "https://github.com/owen282000/life-dashboard-ha"
REPO_STACK = "https://github.com/owen282000/life-dashboard-stack"
APP_STORE = "https://apps.apple.com/app/health-data-for-home-assistant/id6824075761"
APK = f"{REPO}/releases/latest/download/app-release.apk"
PLAY = "https://play.google.com/store/apps/details?id=com.owen282000.lifedashboard"
# Every link to the Play listing carries a campaign referrer naming the page it sits on, so the
# Play Console shows which pages bring installs. Links are written with PLACE in them and each
# page fills it in as it is written (site-landing, site-android, site-guide-<slug>); check()
# refuses a page where it is left. The referrer is URL-encoded and the & is escaped for HTML.
PLACE = "{{place}}"
PLAY_LINK = f"{PLAY}&amp;referrer=utm_source%3D{PLACE}%26utm_medium%3Dwebsite"
# The same for the App Store, in the form App Store Connect counts as a campaign (Analytics,
# Acquisition, Campaigns): the provider token pt is the account's, ct names the page. Links are
# written with CT in them and each page fills it in (site-landing, site-ios, site-guide-<short
# name>, see app_place()). Apple keeps at most CT_MAX characters of a ct; check() refuses a
# longer one and a link to the listing without one. The JSON-LD keeps the plain listing (APP_STORE).
CT = "{{ct}}"
CT_MAX = 40
APP_STORE_LINK = f"https://apps.apple.com/app/apple-store/id6824075761?pt=128699800&amp;ct={CT}&amp;mt=8"


HACS = "https://my.home-assistant.io/redirect/hacs_repository/?owner=owen282000&amp;repository=life-dashboard-ha&amp;category=integration"
# The dashboard cards are add-ons for Home Assistant, not one of the four parts. Each has a
# product page of its own (CARDS below) and is listed with the products in the footer, on the
# landing page and on the integration's page; the bar of the navigation keeps the four parts.
REPO_CARD = "https://github.com/owen282000/life-dashboard-sleep-card"
HACS_CARD = "https://my.home-assistant.io/redirect/hacs_repository/?owner=owen282000&amp;repository=life-dashboard-sleep-card&amp;category=plugin"
REPO_ST_CARD = "https://github.com/owen282000/life-dashboard-screen-time-card"
HACS_ST_CARD = "https://my.home-assistant.io/redirect/hacs_repository/?owner=owen282000&amp;repository=life-dashboard-screen-time-card&amp;category=plugin"


def placed(text, place, ct):
    """A page's HTML with the campaign of its Play links and of its App Store links filled in."""
    return text.replace(PLACE, place).replace(CT, ct)

# ---------------------------------------------------------------------------------------------
# The four parts and where to get them. "kind": "store" is the store the site leads with once it
# is live. Until then, the entry marked "primary" leads, and pending stores show as "Coming".
# Only the structure lives here; every word (names, notes, prices) is in strings.json under
# parts.<slug> and parts.<slug>.get.<id>, and activate() puts the two together as PARTS.
PARTS_BASE = {
    "android": {
        "glyph": '<rect x="6" y="2.5" width="12" height="19" rx="2.5"/><path d="M10.5 18.5h3"/>',
        "get": [
            {"id": "play", "kind": "store", "status": "live", "href": PLAY_LINK},
            {"id": "apk", "status": "live", "href": APK, "primary": True},
            {"id": "obtainium", "status": "live", "href": "https://apps.obtainium.imranr.dev/redirect?r=obtainium://add/" + REPO},
            {"id": "fdroid", "status": "live", "href": "https://f-droid.org/packages/com.owen282000.lifedashboard/"},
        ],
    },
    "ios": {
        "glyph": '<rect x="6" y="2.5" width="12" height="19" rx="3"/><path d="M10 5h4"/>',
        "get": [
            {"id": "appstore", "kind": "store", "status": "live", "href": APP_STORE_LINK},
            {"id": "xcode", "status": "live", "href": REPO_IOS + "#build-and-install", "primary": True},
        ],
    },
    "home-assistant": {
        "glyph": '<path d="M3.5 11 12 3.5l8.5 7.5"/><path d="M5.5 9.5V20h13V9.5"/><circle cx="12" cy="13.5" r="2"/><path d="M12 15.5V20"/>',
        "get": [
            {"id": "hacs", "kind": "store", "status": "live", "href": HACS},
            {"id": "ha-setup", "status": "live", "href": "health-connect-home-assistant/#set-it-up", "rel": True},
            {"id": "ha-source", "status": "live", "href": REPO_HA},
        ],
    },
    "grafana": {
        "glyph": '<path d="M4 20h16"/><path d="M6.5 16v-4"/><path d="M11 16V7"/><path d="M15.5 16v-6"/><path d="M20 16V4"/>',
        "get": [
            {"id": "compose", "kind": "store", "status": "live", "href": REPO_STACK + "#quick-start"},
            {"id": "demo", "status": "live", "href": REPO_STACK + "#try-it-without-a-phone"},
            {"id": "helm", "status": "live", "href": REPO_STACK + "/blob/main/docs/kubernetes.md"},
        ],
    },
    "screen-time-card": {
        "glyph": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
        "get": [
            {"id": "hacs", "kind": "store", "status": "live", "href": HACS_ST_CARD},
            {"id": "card-guide", "status": "live", "href": "screen-time-home-assistant/", "rel": True},
            {"id": "ha-source", "status": "live", "href": REPO_ST_CARD},
        ],
    },
    "sleep-card": {
        "glyph": '<path d="M19.5 14.5A8 8 0 1 1 9.5 4.5a6.5 6.5 0 0 0 10 10z"/>',
        "get": [
            {"id": "hacs", "kind": "store", "status": "live", "href": HACS_CARD},
            {"id": "card-guide", "status": "live", "href": "sleep-stages-home-assistant/", "rel": True},
            {"id": "ha-source", "status": "live", "href": REPO_CARD},
        ],
    },
}
ORDER = ["android", "ios", "home-assistant", "grafana"]
# The dashboard cards: product pages like the four parts, but not in the bar of the navigation,
# the install section's four cards or the "four parts" the texts count.
CARDS = ["screen-time-card", "sleep-card"]
PRODUCTS = ORDER + CARDS
# The links at the foot of a card's page: what it sits on, and the other card.
CARD_SIBLINGS = {"screen-time-card": ["home-assistant", "android", "sleep-card"],
                 "sleep-card": ["home-assistant", "android", "ios", "screen-time-card"]}

# One sentence per app about where to get it, used through {{status:android}} and {{status:ios}}:
# "status" in strings.json, set per language by activate().
# Phrases that must be gone once a store is live (checked on every build).
STALE = {"play": ["coming to Google Play", "Google Play is in closed testing", "will be a paid listing", "Google Play: coming",
                  "Google Play (paid) is coming", "Closed testing", "closed testing", "In closed testing",
                  "store listings that are on the way", "A Google Play listing will come", "Google Play is next",
                  "Free APK today"],
         "appstore": ["App Store release is planned", "no App Store", "Planned after the TestFlight beta",
                      "TestFlight beta is next", "TestFlight beta next", "A public beta is next",
                      "in App Store review", "In App Store review", "in Apple's review", "in Apple&#x27;s review"],
         "fdroid": ["F-Droid is reviewing", "F-Droid has accepted", "Accepted by F-Droid", "listing goes live with"],
         "play_paid": []}

# Official badge artwork, stored in img/badges/ (the site loads nothing from anyone else), keyed
# by the PARTS route id: file, alt text, the file's own pixel size, and the caption shown while
# the route is "soon". Sources: Google Play from play.google.com/intl/en_us/badges, the App
# Store from toolbox.marketingtools.apple.com, F-Droid from F-Droid's artwork repository
# (fdroid.gitlab.io/artwork/badge/get-it-on.svg), Obtainium from its repository
# (assets/graphics/badge_obtainium.png). HACS, Artifact Hub and Docker Compose have no store
# badge, so hacs.svg, artifact-hub.svg and docker-compose.svg are drawn in the shape of the
# F-Droid and GitHub badges, around the official HACS and Artifact Hub icons, unaltered (the
# sources are named inside each file), and the official Docker logo from Docker's media kit,
# unaltered. Their lettering is Roboto (SIL OFL) converted to outlines, so it renders the same
# everywhere. AlternativeTo has no black badge, so alternativeto.svg is their compact badge on the
# shared black frame, with their logo mark and lettering unchanged.
# Every file is cropped to the edge of its visible badge (the transparent margin of the Play,
# F-Droid, Obtainium and GitHub files is cut from these copies; the artwork is untouched), so one
# CSS height gives every badge the same visible height (.badge-img in site.css).
BADGE_FILES = {"play": ("google-play.png", (564, 168)),
               "appstore": ("app-store.svg", (120, 40)),
               "fdroid": ("f-droid.svg", (564, 168)),
               "obtainium": ("obtainium.png", (564, 168)),
               "hacs": ("hacs.svg", (564, 168)),
               "compose": ("docker-compose.svg", (877, 168)),
               "helm": ("artifact-hub.svg", (684, 168)),
               "apk": ("github.svg", (564, 168))}
# GitHub has no official badge; this one is the open-source "Get it on GitHub" badge from
# github.com/Kunzisoft/Github-badge (CC BY-SA 3.0, made from F-Droid's badge template), credited
# in the footer like the F-Droid badge (CC BY-SA 3.0). It links to the release page, not the file.
BADGE_HREF = {"apk": REPO + "/releases/latest",
              "helm": "https://artifacthub.io/packages/helm/life-dashboard/life-dashboard"}

# The landing page and the guide index group the guides under these headings (their words are
# guide_groups.<key> in strings.json); every guide sits in exactly one.
GROUPS = [
    ("home-assistant", ["health-connect-home-assistant", "companion-app-health-connect",
                        "sleep-stages-home-assistant", "screen-time-home-assistant",
                        "smart-scale-to-samsung-health"]),
    ("watch-brands", ["samsung-health-home-assistant", "fitbit-home-assistant", "garmin-home-assistant",
                      "samsung-health-export"]),
    ("your-own-server", ["health-connect-webhook", "health-connect-n8n", "health-data-api", "health-data-own-ai",
                         "health-data-qr-pairing"]),
    ("iphone", ["apple-health-home-assistant", "apple-health-home-assistant-apps", "apple-watch-home-assistant",
                "apple-health-webhook", "apple-health-n8n", "apple-health-data-types"]),
    ("reference", ["health-connect-data-types", "health-connect-steps-home-assistant", "troubleshooting"]),
]
# The guides, in the order of the footer and the lists. Each is i18n/<lang>/guides/<id>.html;
# its name, one-line description and closing call to action are guides.<id> in
# strings.json.
GUIDE_IDS = [
    "health-connect-home-assistant", "samsung-health-home-assistant", "companion-app-health-connect",
    "health-connect-webhook", "screen-time-home-assistant", "sleep-stages-home-assistant",
    "smart-scale-to-samsung-health", "health-connect-n8n", "health-connect-data-types", "health-data-api",
    "samsung-health-export", "fitbit-home-assistant", "garmin-home-assistant", "health-data-own-ai",
    "health-data-qr-pairing", "health-connect-steps-home-assistant", "troubleshooting",
    "apple-health-home-assistant", "apple-health-home-assistant-apps", "apple-watch-home-assistant",
    "apple-health-webhook", "apple-health-n8n", "apple-health-data-types",
]
GUIDE_ABOUT = {
    "health-connect-n8n": ["#android", "#ios"],
    "health-connect-data-types": ["#android", "#ios"],
    "samsung-health-home-assistant": ["#android", "#integration"],
    "companion-app-health-connect": ["#android", "#integration"],
    "health-data-api": ["#android", "#ios"],
    "samsung-health-export": ["#android"],
    "fitbit-home-assistant": ["#android", "#integration"],
    "garmin-home-assistant": ["#android", "#integration"],
    "health-data-own-ai": ["#stack", "#integration", "#android", "#ios"],
    "health-data-qr-pairing": ["#android", "#ios"],
    "health-connect-home-assistant": ["#android", "#integration"],
    "health-connect-webhook": ["#android", "#ios"],
    "screen-time-home-assistant": ["#screen-time-card", "#android", "#integration"],
    "sleep-stages-home-assistant": ["#sleep-card", "#integration", "#android", "#ios"],
    "smart-scale-to-samsung-health": ["#integration", "#android"],
    "troubleshooting": ["#android", "#integration", "#ios"],
    "health-connect-steps-home-assistant": ["#android", "#integration"],
    "apple-health-home-assistant": ["#ios", "#integration"],
    "apple-health-home-assistant-apps": ["#ios", "#integration"],
    "apple-watch-home-assistant": ["#ios", "#integration"],
    "apple-health-webhook": ["#ios", "#stack"],
    "apple-health-n8n": ["#ios"],
    "apple-health-data-types": ["#ios"],
}

# kind, width and height of each screenshot; its alt text is images.<name> in strings.json.
IMAGE_FILES = {
    "A1-health": ("phone", 720, 1600),
    "A2-pair": ("phone", 720, 1600),
    "A4-screen-time": ("phone", 720, 1600),
    "A5-receive": ("phone", 720, 1600),
    "A6-webhook": ("phone", 720, 1600),
    "A7-logs": ("phone", 720, 1600),
    "H2-qr": ("card", 800, 668),
    "H6-health": ("wide", 1400, 807),
    "H7-screen-time": ("wide", 1400, 1032),
    "H8-two-phones": ("wide", 1400, 875),
    "H9-health-phone": ("phone", 720, 1559),
    "ios-health": ("phone", 720, 1464),
    "ios-schedule": ("phone", 720, 1464),
    "ios-logs": ("phone", 720, 1464),
    "ios-mqtt": ("phone", 720, 1464),
    "ios-webhook": ("phone", 720, 1464),
    "p-pairing-flow": ("diagram", 1400, 700),
    "S1-sleep-card": ("wide", 1400, 442),
    "S2-sleep-card-phone": ("card", 720, 531),
    "T1-screen-time-cards": ("wide", 1400, 575),
    "T2-screen-time-card-phone": ("card", 720, 999),
    "T3-screen-time-week": ("card", 720, 796),
    "T4-screen-time-family": ("card", 720, 753),
    "g-overview": ("wide", 1400, 728),
    "g-activity": ("wide", 1400, 1260),
    "g-sleep": ("wide", 1400, 895),
    "g-heart-body": ("wide", 1400, 1363),
    "g-screen-time": ("wide", 1400, 1196),
    "g-data": ("wide", 1400, 1260),
}

# Phone screenshots cut short of the full screen; they fade out at the bottom.
CUT = set()

# A line shown with the image, in a figure's caption or on a product page's stage.
# The line itself is captions.<name> in strings.json.
CAPTIONED = ["S1-sleep-card", "S2-sleep-card-phone", "T1-screen-time-cards", "T2-screen-time-card-phone",
             "T3-screen-time-week", "T4-screen-time-family"]
# A product page shows this image instead on a phone, where the wide one would be too small to read.
PHONE_SHOT = {"S1-sleep-card": "S2-sleep-card-phone", "T1-screen-time-cards": "T2-screen-time-card-phone"}

# How each guide closes: the buttons under its last section, as (class, address). The sentence
# above them and their labels are guides.<id>.next and guides.<id>.buttons in strings.json.
NEXT_BUTTONS = {
    "health-connect-steps-home-assistant": [("btn-primary btn-store", "../android/#get"), ("btn-ghost", "../health-connect-home-assistant/")],
    "troubleshooting": [("btn-primary", f"{REPO}/discussions"), ("btn-ghost", f"{REPO}/blob/main/docs/usage.md#troubleshooting")],
    "health-connect-n8n": [("btn-primary btn-store", "../android/#get"), ("btn-ghost", f"{REPO}/blob/main/docs/webhook.md#n8n-and-node-red")],
    "health-connect-data-types": [("btn-primary btn-store", "../android/#get"), ("btn-ghost", f"{REPO}/blob/main/docs/webhook.md#health-connect-data-types")],
    "samsung-health-home-assistant": [("btn-primary btn-store", HACS), ("btn-ghost", "../android/#get")],
    "companion-app-health-connect": [("btn-primary btn-store", HACS), ("btn-ghost", "../android/#get")],
    "health-data-api": [("btn-primary btn-store", "../android/#get"), ("btn-ghost", "../ios/#get")],
    "samsung-health-export": [("btn-primary btn-store", "../android/#get"), ("btn-ghost", f"{REPO}/blob/main/docs/webhook.md")],
    "fitbit-home-assistant": [("btn-primary btn-store", HACS), ("btn-ghost", "../android/#get")],
    "garmin-home-assistant": [("btn-primary btn-store", HACS), ("btn-ghost", "../android/#get")],
    "health-data-own-ai": [("btn-primary btn-store", "../grafana/#your-own-ai"), ("btn-ghost", "../home-assistant/")],
    "health-connect-home-assistant": [("btn-primary btn-store", HACS), ("btn-ghost", "../android/#get")],
    "health-data-qr-pairing": [("btn-primary", f"{REPO}/blob/main/docs/pairing.md"), ("btn-ghost", f"{REPO}/blob/main/docs/webhook.md")],
    "sleep-stages-home-assistant": [("btn-primary btn-store", HACS_CARD), ("btn-ghost", REPO_CARD)],
    "health-connect-webhook": [("btn-primary btn-store", "../android/#get"), ("btn-ghost", f"{REPO}/blob/main/docs/webhook.md")],
    "screen-time-home-assistant": [("btn-primary btn-store", "../android/#get"), ("btn-ghost", HACS)],
    "smart-scale-to-samsung-health": [("btn-primary btn-store", HACS), ("btn-ghost", "../android/#get")],
    "apple-health-home-assistant": [("btn-primary btn-store", HACS), ("btn-ghost", "../ios/#get")],
    "apple-health-home-assistant-apps": [("btn-primary btn-store", "../ios/#get"), ("btn-ghost", "../apple-health-home-assistant/")],
    "apple-watch-home-assistant": [("btn-primary btn-store", HACS), ("btn-ghost", "../ios/#get")],
    "apple-health-webhook": [("btn-primary btn-store", "../ios/#get"), ("btn-ghost", f"{REPO_IOS}/blob/main/docs/webhook.md")],
    "apple-health-n8n": [("btn-primary btn-store", "../ios/#get"), ("btn-ghost", f"{REPO}/blob/main/docs/webhook.md#n8n-and-node-red")],
    "apple-health-data-types": [("btn-primary btn-store", "../ios/#get"), ("btn-ghost", f"{REPO_IOS}/blob/main/docs/webhook.md#what-ios-sends")],
}

# Structured data for the project and its four parts, written into the landing page and, for
# each part, into its own product page.
ME = {"@type": "Person", "@id": f"{BASE}#owen", "name": "Owen Vogelaar", "url": DOMAIN,
      "sameAs": ["https://github.com/owen282000"], "worksFor": {"@id": f"{DOMAIN}#org"}}
# The business behind the site, as the footer's imprint names it.
ORG = {"@type": "Organization", "@id": f"{DOMAIN}#org", "name": "oVog Enterprise", "url": DOMAIN,
       "logo": f"{DOMAIN}img/ov-180.png", "email": "owen282000@hotmail.com", "founder": {"@id": f"{BASE}#owen"},
       "sameAs": ["https://github.com/owen282000"]}
WEBSITE = {"@type": "WebSite", "@id": f"{BASE}#website", "url": BASE, "name": "Life Dashboard",
           "inLanguage": [m["hreflang"] for m in LANGS.values()], "publisher": {"@id": f"{DOMAIN}#org"}}
PROJECT_BASE = {"@type": "CreativeWorkSeries", "@id": f"{BASE}#project", "name": "Life Dashboard", "url": BASE,
                "author": {"@id": f"{BASE}#owen"},
                "hasPart": [{"@id": f"{BASE}#android"}, {"@id": f"{BASE}#ios"}, {"@id": f"{BASE}#integration"}, {"@id": f"{BASE}#stack"},
                            {"@id": f"{BASE}#screen-time-card"}, {"@id": f"{BASE}#sleep-card"}]}
ENTITY_ID = {"android": "#android", "ios": "#ios", "home-assistant": "#integration", "grafana": "#stack",
             "screen-time-card": "#screen-time-card", "sleep-card": "#sleep-card"}
ENTITY_BASE = {
    "android": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#android", "name": "Life Dashboard Companion",
        "alternateName": ["Life Dashboard", "Life Dashboard Companion for Android", "Health Data for Home Assistant"],
        "identifier": "com.owen282000.lifedashboard",
        "applicationCategory": "HealthApplication",
        "inLanguage": ["en", "nl", "de", "fr", "es", "it", "pt-BR", "ja", "ar", "hi", "zh-Hans"], "url": f"{BASE}android/",
        "downloadUrl": f"{REPO}/releases/latest", "license": "https://opensource.org/licenses/MIT",
        "isPartOf": {"@id": f"{BASE}#project"}, "author": {"@id": f"{BASE}#owen"},
        "sameAs": [REPO], "screenshot": f"{BASE}img/A1-health.webp"},
    "ios": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#ios", "name": "Life Dashboard Companion for iPhone",
        "alternateName": ["Life Dashboard Companion for iOS", "Health Data for Home Assistant"], "applicationCategory": "HealthApplication",
        "inLanguage": ["en", "nl", "de", "fr", "es", "it", "pt-BR", "ja", "ar", "hi", "zh-Hans"], "url": f"{BASE}ios/", "license": "https://opensource.org/licenses/MIT",
        "isPartOf": {"@id": f"{BASE}#project"}, "author": {"@id": f"{BASE}#owen"},
        "sameAs": [REPO_IOS], "screenshot": f"{BASE}img/ios-health.webp"},
    "home-assistant": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#integration", "name": "Life Dashboard integration for Home Assistant",
        "applicationCategory": "UtilitiesApplication", "url": f"{BASE}home-assistant/",
        "license": "https://opensource.org/licenses/MIT", "isPartOf": {"@id": f"{BASE}#project"},
        "author": {"@id": f"{BASE}#owen"}, "sameAs": [REPO_HA]},
    "grafana": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#stack", "name": "Life Dashboard stack",
        "applicationCategory": "UtilitiesApplication", "url": f"{BASE}grafana/",
        "license": "https://opensource.org/licenses/MIT", "isPartOf": {"@id": f"{BASE}#project"},
        "author": {"@id": f"{BASE}#owen"}, "sameAs": [REPO_STACK]},
    "screen-time-card": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#screen-time-card", "name": "Life Dashboard Screen Time",
        "alternateName": ["Life Dashboard Screen Time cards", "life-dashboard-screen-time-card"],
        "applicationCategory": "UtilitiesApplication", "url": f"{BASE}screen-time-card/",
        "inLanguage": ["en", "nl", "de", "fr", "es", "it", "pt", "ja", "ar", "hi", "zh"],
        "downloadUrl": f"{REPO_ST_CARD}/releases/latest", "license": "https://opensource.org/licenses/MIT",
        "isPartOf": {"@id": f"{BASE}#project"}, "author": {"@id": f"{BASE}#owen"},
        "sameAs": [REPO_ST_CARD], "screenshot": f"{BASE}img/T1-screen-time-cards.webp"},
    "sleep-card": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#sleep-card", "name": "Life Dashboard Sleep Card",
        "alternateName": "life-dashboard-sleep-card",
        "applicationCategory": "UtilitiesApplication", "url": f"{BASE}sleep-card/",
        "downloadUrl": f"{REPO_CARD}/releases/latest", "license": "https://opensource.org/licenses/MIT",
        "isPartOf": {"@id": f"{BASE}#project"}, "author": {"@id": f"{BASE}#owen"},
        "sameAs": [REPO_CARD], "screenshot": f"{BASE}img/S1-sleep-card.webp"},
}
ENTITY_NAME = {ENTITY_ID[k]: e["name"] for k, e in ENTITY_BASE.items()}

# Every part is free to download (the APK, the source, HACS, Compose). Each paid store listing
# has an Offer of its own next to the free one: the App Store and Google Play. The JSON-LD links
# the listing itself, without a campaign referrer (HTML entities don't apply inside a script).
FREE = {"@type": "Offer", "price": "0", "priceCurrency": "EUR"}
for _e in ENTITY_BASE.values():
    _e["offers"] = FREE
ENTITY_BASE["ios"]["offers"] = [FREE, {"@type": "Offer", "price": "6.99", "priceCurrency": "EUR", "url": APP_STORE}]
ENTITY_BASE["ios"]["sameAs"] = [REPO_IOS, APP_STORE]
ENTITY_BASE["android"]["offers"] = [FREE, {"@type": "Offer", "price": "4.99", "priceCurrency": "EUR", "url": PLAY}]
ENTITY_BASE["android"]["sameAs"] = [REPO, PLAY]
SOURCE_CODE = {"@type": "SoftwareSourceCode", "codeRepository": REPO, "programmingLanguage": "Kotlin",
               "license": "https://opensource.org/licenses/MIT", "targetProduct": {"@id": f"{BASE}#android"}}

# ---------------------------------------------------------------------------------------------
# Pages. Every page has an id and an English address; a translation lives under its language's
# folder at the same address (/de/life-dashboard/android/), except that a guide may carry a
# local slug (`slug:` in its header). A page exists in a language once its source file does:
# i18n/<lang>/guides/<id>.html, products/<id>.json or pages/<id>.html. The guide index is made
# from strings.json alone, so it exists once its title (ui.index.title) is translated.
PAGES = {"hub": "", "privacy": "privacy/", "legal": "legal/", "landing": "life-dashboard/", "guides": "life-dashboard/guides/",
         **{s: f"life-dashboard/{s}/" for s in PRODUCTS}, **{g: f"life-dashboard/{g}/" for g in GUIDE_IDS},
         "ios-privacy": "life-dashboard/ios/privacy/"}
EN_PATH_TO_ID = {"/" + p: pid for pid, p in PAGES.items()}
HAND_PAGES = {"hub": "hub", "privacy": "privacy", "landing": "landing", "ios-privacy": "ios-privacy"}
# Pages without a source file of their own, made from strings.json alone: each exists in a
# language once its title is translated.
STRING_PAGES = {"guides": "ui.index.title", "legal": "ui.legal.title"}
# The Play campaign source of each page (P1-36): the English names stay as they were, a
# translation adds its language (site-de-guide-<id>).
PLACES = {"landing": "landing", "guides": "guides", "hub": "hub", "privacy": "privacy", "legal": "legal", "ios-privacy": "ios-privacy",
          **{s: s for s in PRODUCTS}, **{g: f"guide-{g}" for g in GUIDE_IDS}}
# The App Store campaign of a page has the same shape, but Apple keeps 40 characters, so a guide
# goes by a short name: its id without "home-assistant" (where nearly every guide leads) and with
# "health-connect" written "hc" (site-guide-samsung-health, site-de-guide-hc-webhook). An id
# that is still too long gets its short name here.
GUIDE_SHORT = {"smart-scale-to-samsung-health": "smart-scale"}


def app_place(pid, lang):
    """The App Store campaign (ct) of a page: site-ios, site-de-guide-hc-webhook."""
    short = PLACES[pid]
    if pid in GUIDE_IDS:
        short = "guide-" + GUIDE_SHORT.get(pid, pid.replace("-home-assistant", "")
                                           .replace("health-connect", "hc"))
    return "site-" + ("" if lang == "en" else lang + "-") + short


def source(pid, lang):
    if pid in GUIDE_IDS:
        return I18N / lang / "guides" / f"{pid}.html"
    if pid in PRODUCTS:
        return I18N / lang / "products" / f"{pid}.json"
    if pid in HAND_PAGES:
        return I18N / lang / "pages" / f"{HAND_PAGES[pid]}.html"
    return None


def exists(pid, lang):
    if lang == "en":
        return True
    if lang not in STRINGS:
        return False
    if pid in STRING_PAGES:
        return bool(lookup(STRINGS[lang], STRING_PAGES[pid]))
    return source(pid, lang).exists()


def header_of(src):
    """The comment a source file opens with: `key: value` lines, then free notes."""
    m = re.match(r"\s*<!--(.*?)-->", src, re.S)
    return m.group(1) if m else ""


def opt_meta(src, key):
    m = re.search(rf"^\s*{key}:\s*(.+)$", header_of(src), re.M)
    return m.group(1).strip() if m else None


def meta(src, key):
    v = opt_meta(src, key)
    if not v:
        sys.exit(f"missing {key}")
    return v


def body_of(src):
    """A source file without its header comment."""
    return re.sub(r"\s*<!--.*?-->", "", src, count=1, flags=re.S)


SLUGS = {}
for _lang in LANGS:
    for _g in GUIDE_IDS:
        if exists(_g, _lang):
            SLUGS[(_g, _lang)] = (opt_meta(source(_g, _lang).read_text(), "slug") if _lang != "en" else None) or _g


def path_of(pid, lang):
    p = f"life-dashboard/{SLUGS[(pid, lang)]}/" if pid in GUIDE_IDS else PAGES[pid]
    d = LANGS[lang]["dir"]
    return (d + "/" if d else "") + p


def url_of(pid, lang=None):
    return DOMAIN + path_of(pid, lang or L)


def alternates(pid):
    """The hreflang links of a page: itself, every translation and x-default (English). Empty
    while a page has no translation yet."""
    langs = [c for c in LANGS if exists(pid, c)]
    if len(langs) < 2:
        return []
    out = []
    for c in langs:
        out += [(h, url_of(pid, c)) for h in [LANGS[c]["hreflang"]] + LANGS[c].get("extra_hreflang", [])]
    return out + [("x-default", url_of(pid, "en"))]


_HASH = {}


def version(path):
    """A short hash of a stylesheet or image, so a changed file is a new URL: Cloudflare and
    browsers keep the old one for a week otherwise (Cache-Control in the Caddyfile)."""
    if path not in _HASH:
        f = SITE / path.lstrip("/")
        ok = f.is_file() and f.suffix in (".css", ".png", ".webp", ".svg", ".ico", ".jpg")
        _HASH[path] = hashlib.sha256(f.read_bytes()).hexdigest()[:8] if ok else ""
    return _HASH[path]


def localize(doc, pid, lang):
    """Every href, src and srcset of a page, as the site serves it. Sources and templates write
    links as on the English page (relative to it, or from the root). A link to a page becomes
    that page in this language, or stays English, marked hreflang="en", while the translation
    is missing. A file gets its address from the root and its content hash. A value that starts
    with "=" is final (the language menu) and loses only that mark."""
    base = "https://x/" + PAGES[pid]

    def fix(m):
        attr, val = m.group(1), m.group(2)
        if val.startswith("="):
            return f'{attr}="{val[1:]}"'
        if not val or val.startswith(("#", "http://", "https://", "mailto:", "data:")):
            return m.group(0)
        u = urlsplit(urljoin(base, html.unescape(val)))
        frag = "#" + u.fragment if u.fragment else ""
        if attr == "href" and u.path in EN_PATH_TO_ID:
            target = EN_PATH_TO_ID[u.path]
            if exists(target, lang):
                return f'href="/{path_of(target, lang)}{frag}"'
            return f'href="{u.path}{frag}"' + (' hreflang="en"' if lang != "en" else "")
        v = version(u.path)
        query = f"?v={v}" if v else ("?" + html.escape(u.query) if u.query else "")
        return f'{attr}="{u.path}{query}{frag}"'
    doc = re.sub(r'\b(href|src|srcset)="([^"]*)"', fix, doc)
    # F-Droid is written plainly in every source. In the text of a page its hyphen must not
    # break at the end of a line; in the <head>, in attributes and in code it stays as typed.
    cut = doc.find("</head>") + 1
    return doc[:cut] + re.sub(r">[^<]*F-Droid[^<]*<", lambda m: m.group(0).replace("F-Droid", "F&#8209;Droid"),
                              re.sub(r"(<(pre|code)\b.*?</\2>)", lambda m: m.group(0).replace("F-Droid", "F\0Droid"), doc[cut:], flags=re.S)
                              ).replace("F\0Droid", "F-Droid")


BUILT = {}   # (page id, language) -> the file written


def emit(pid, lang, doc):
    """Write one page: its Play and App Store campaigns filled in, its links localized."""
    place = "site-" + ("" if lang == "en" else lang + "-") + PLACES[pid]
    f = SITE / path_of(pid, lang) / "index.html"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(localize(placed(doc, place, app_place(pid, lang)), pid, lang))
    BUILT[(pid, lang)] = f


def activate(lang):
    """Set the language being built: the tables below are the structure above with this
    language's words from strings.json (English where a word is still missing)."""
    global L, PARTS, STATUS_TEXT, BADGES, GUIDES, GUIDE_NAMES, GUIDE_GROUPS, NEXT, IMAGES, CAPTIONS, ENTITIES, PROJECT
    L = lang
    PARTS = {}
    for slug, base in PARTS_BASE.items():
        words = EN["parts"][slug]
        PARTS[slug] = {**base, **{k: S(f"parts.{slug}.{k}") for k in words if k != "get"},
                       "get": [{**it, **{k: S(f"parts.{slug}.get.{it['id']}.{k}") for k in words["get"][it["id"]]}}
                               for it in base["get"]]}
    STATUS_TEXT = {k: S(f"status.{k}") for k in EN["status"]}
    BADGES = {k: (f, S(f"badges.{k}.alt"), size, S(f"badges.{k}.soon") if "soon" in EN["badges"][k] else "")
              for k, (f, size) in BADGE_FILES.items()}
    GUIDES = [(g, S(f"guides.{g}.name"), "", S(f"guides.{g}.desc")) for g in GUIDE_IDS]
    GUIDE_NAMES = {g[0]: g[1] for g in GUIDES}
    GUIDE_GROUPS = [(S(f"guide_groups.{k}"), slugs) for k, slugs in GROUPS]
    NEXT = {}
    for g in GUIDE_IDS:
        labels = S(f"guides.{g}.buttons")
        # A language may replace a guide's buttons outright: a list of {"class", "href", "label"}.
        buttons = ([(b["class"], b["href"], b["label"]) for b in labels] if labels and isinstance(labels[0], dict)
                   else [(c, h, label) for (c, h), label in zip(NEXT_BUTTONS[g], labels)])
        NEXT[g] = (S(f"guides.{g}.next"), buttons)
    IMAGES = {k: (kind, w, h, S(f"images.{k}")) for k, (kind, w, h) in IMAGE_FILES.items()}
    CAPTIONS = {k: S(f"captions.{k}") for k in CAPTIONED}
    ENTITIES = {k: {**e, **{f: S(f"entities.{k}.{f}") for f in EN["entities"][k]}} for k, e in ENTITY_BASE.items()}
    PROJECT = {**PROJECT_BASE, "description": S("project_description")}


GH = '<svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'

# Plain glyphs for the buttons. Not the stores' logos: a store gets its official badge.
# Why this style: drawn by hand on a 24 grid with a 2 px round-capped stroke, the same line as the
# heartbeat mark in the app icon, so they read as part of that mark; each one draws the thing it
# labels (a phone, a house, chart bars, a download arrow) and none comes from an icon library.
ICONS = {
    "play": '<path d="M7 4.5v15l12-7.5z"/>',
    "appstore": '<rect x="3.5" y="3.5" width="17" height="17" rx="4.5"/><path d="M9 16l3-8 3 8M10.2 13h3.6"/>',
    "fdroid": '<rect x="4" y="8" width="16" height="11" rx="2.5"/><path d="M8 8 6.5 5M16 8l1.5-3"/><circle cx="9.5" cy="13" r="1"/><circle cx="14.5" cy="13" r="1"/>',
    "obtainium": '<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v4.5h-4.5"/>',
    "apk": '<path d="M12 4v11m0 0-4.5-4.5M12 15l4.5-4.5M5 20h14"/>',
    "testflight": '<path d="M21 3 10 14"/><path d="M21 3l-7 18-4-7-7-4z"/>',
    "xcode": '<path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/>',
    "hacs": '<path d="M3.5 11 12 3.5l8.5 7.5"/><path d="M5.5 9.5V20h13V9.5"/>',
    "ha-source": '<path d="m8 7-5 5 5 5M16 7l5 5-5 5"/>',
    "ha-setup": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6h.01M4 12h.01M4 18h.01"/>',
    "card-guide": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6h.01M4 12h.01M4 18h.01"/>',
    "compose": '<rect x="3.5" y="9" width="17" height="10" rx="2"/><path d="M7 9V6h4v3M13 9V6h4v3"/>',
    "demo": '<path d="M4 19V5m0 14h16M8 15v-3m4 3V9m4 6v-5m4 5V7"/>',
    "helm": '<circle cx="12" cy="12" r="6.5"/><circle cx="12" cy="12" r="2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
}


def svg(path, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f'<svg{c} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>'


def badge(item, prefix=""):
    """The official badge of a route. Live: a link. Pending: the same unaltered badge, not a
    link, in a dashed frame with a "Coming soon" caption (stores forbid recoloring or fading)."""
    f, alt, (w, h), soon = BADGES[item["id"]]
    img = f'<img class="badge-img" src="{prefix}img/badges/{f}" alt="{alt}" width="{w}" height="{h}" loading="lazy">'
    if item["status"] == "live":
        return f'<a class="badge-link" href="{BADGE_HREF.get(item["id"]) or href_of(item, prefix)}">{img}</a>'
    detail = f' <span>{soon}</span>' if soon else ""
    return f'<span class="badge-soon">{img}<small><b>{t("coming_soon")}</b>{detail}</small></span>'


def has_badge(item):
    return item["id"] in BADGES


def badge_row(items, prefix=""):
    """The live badges in one row, the ones still coming in a row of their own under it, each in
    PARTS order, so a framed "Coming soon" badge never sits between two plain ones."""
    rows = []
    for live in (True, False):
        shown = [badge(it, prefix) for it in items if has_badge(it) and (it["status"] == "live") == live]
        if shown:
            rows.append(f'<div class="badges">{"".join(shown)}</div>')
    if len(rows) == 2:
        return f'<div class="badge-rows">{"".join(rows)}</div>'
    return rows[0] if rows else ""


def store_button(item, fallback, prefix=""):
    """A route with an official badge shows the badge (linked when live, framed as coming soon
    otherwise). A live route without one (Compose) gets a store-style button."""
    if has_badge(item):
        return badge(item, prefix)
    return lead_button(dict(item, kind=""), prefix)


def store_of(slug):
    return next((it for it in PARTS[slug]["get"] if it.get("kind") == "store"), None)


def lead_item(slug):
    """What a hero or card leads with: the store once it's live, otherwise the primary route."""
    store = store_of(slug)
    if store and store["status"] == "live":
        return store
    return next(it for it in PARTS[slug]["get"] if it.get("primary"))


def free_follows(slug, lead):
    """True when a live store leads a part that also has free routes (Android: Google Play, then
    GitHub, Obtainium and F-Droid). The store's pitch and the free routes then follow its badge."""
    return lead.get("kind") == "store" and bool(PARTS[slug].get("free_line")) and bool(lead.get("pitch"))


def href_of(item, prefix=""):
    return prefix + item["href"] if item.get("rel") else item["href"]


def lead_button(item, prefix=""):
    if item.get("kind") == "store":
        return store_button(item, "", prefix)
    return f'<a class="btn btn-primary btn-store" href="{href_of(item, prefix)}">{svg(ICONS[item["id"]])}{item.get("cta", item["name"])}</a>'


def alt_links(items, prefix="", sep=" · "):
    out = []
    for it in items:
        if it["status"] == "live":
            out.append(f'<a class="nowrap" href="{href_of(it, prefix)}">{it["name"]}</a>')
        else:
            out.append(f'<span class="soon-tag">{it.get("soon_text") or t("coming_named", name=it["name"])}</span>')
    return sep.join(out)


def get_card_compact(slug, prefix):
    """The landing page's install card: the lead button and one line with the other routes.
    The full card, with a note per route, is on the product page."""
    p = PARTS[slug]
    lead = lead_item(slug)
    rest = [it for it in p["get"] if it is not lead]
    plain = [it for it in rest if not has_badge(it)]
    alt = f'\n        <p class="get-alt">{alt_links(plain, prefix)}</p>' if plain else ""
    # An install card with a badged lead (the APK on GitHub, HACS) shows one row of badges, so the
    # same download never appears twice side by side; heroes keep the plain primary button.
    top = badge_row([lead] + rest, prefix) if has_badge(lead) else lead_button(lead, prefix) + "\n        " + badge_row(rest, prefix)
    if free_follows(slug, lead):
        top = (f'<div class="badges">{badge(lead, prefix)}</div>\n        <p class="get-alt">{lead["pitch"]} {p["free_line"]}</p>'
               f'\n        {badge_row(rest, prefix)}')
    elif lead.get("pitch"):
        # The App Store: its price under the badge, as under the Play badge.
        top += f'\n        <p class="get-alt">{lead["pitch"]}</p>'
    return f"""<article class="get-card compact" id="get-{slug}">
        <header><span class="part-ico">{svg(p["glyph"])}</span><div><h3><a href="{prefix}{slug}/">{p["full"]}</a></h3><p>{p["req_short"]}</p></div></header>
        {top}{alt}
      </article>"""


def get_card(slug, prefix, req=True):
    p = PARTS[slug]
    page = f"{prefix}{slug}/"
    lead = lead_item(slug)
    rows = []
    for it in sorted(p["get"], key=lambda it: has_badge(it) and it["status"] != "live"):
        if it is lead:
            continue
        live = it["status"] == "live"
        if has_badge(it):
            rows.append(f'<li class="with-badge">{badge(it, prefix)}<small>{it["note"]}</small></li>')
            continue
        tag = f'<span class="status live">{t("available")}</span>' if live else f'<span class="status soon">{t("coming")}</span>'
        name = f'<a href="{href_of(it, prefix)}">{it["name"]}</a>' if live else it["name"]
        rows.append(f'<li>{svg(ICONS[it["id"]], "li-ico")}<span><b>{name}</b> {tag}<small>{it["note"]}</small></span></li>')
    note = f'<p class="store-note">{lead["note"]}</p>' if lead.get("note") else ""
    if free_follows(slug, lead):
        rows.insert(0, f'<li class="free-line">{p["free_line"]}</li>')
    reqs = f'<p class="get-req">{p["requires"]}</p>' if req else ""
    title = f'<a href="{page}">{p["full"]}</a>'
    return f"""<article class="get-card" id="get-{slug}">
        <header><span class="part-ico">{svg(p["glyph"])}</span><div><h3>{title}</h3><p>{p["line"]}</p></div></header>
        {badge(lead, prefix) if has_badge(lead) else lead_button(lead, prefix)}
        {note}
        <ul class="get-list">
          {"".join(rows)}
        </ul>
        {reqs}
      </article>"""


def get_section(prefix):
    cards = "\n      ".join(get_card_compact(s, prefix) for s in ORDER)
    # The three steps that used to sit under the flow diagram, told once, here where they happen.
    return f"""<div class="section-head">
      <h2>{t("get.title")}</h2>
      <p>{t("get.intro")}</p>
    </div>
    <ol class="get-steps">
      <li>{t("get.step1")}</li>
      <li>{t("get.step2")}</li>
      <li>{t("get.step3")}</li>
    </ol>
    <div class="get-grid">
      {cards}
    </div>
    {cards_block(prefix, "get-cards")}"""


def cards_block(prefix, cls):
    """The two dashboard cards under a heading of their own: with their Marketplace badge in
    the landing page's install section, as links on the integration's page."""
    if cls == "get-cards":
        items = "\n      ".join(get_card_compact(c, prefix) for c in CARDS)
        grid = f'<div class="get-grid">\n      {items}\n    </div>'
    else:
        items = "\n      ".join(part_link(c) for c in CARDS)
        grid = f'<div class="family two">\n      {items}\n    </div>'
    return f"""<div class="section-head sub-head" id="cards">
      <h3>{t("cards.title")}</h3>
      <p>{t("cards.intro")}</p>
    </div>
    {grid}"""


def part_link(s):
    """A part or a card as a link: its glyph, its name, one line and where it leads."""
    return (f'<a class="part" href="{LD}{s}/"><span class="part-ico">{svg(PARTS[s]["glyph"])}</span><h3>{PARTS[s]["full"]}</h3>'
            f'<p>{PARTS[s]["line"]}</p><span class="go">{PARTS[s]["more"]}</span></a>')


def android_paths(prefix):
    """The Android line in the hero: Google Play, with the free routes after it."""
    return t("hero.android", pitch=store_of("android")["pitch"])


def ios_paths(prefix):
    """The iPhone line in the hero: the App Store, and building it yourself."""
    return t("hero.ios", pitch=store_of("ios")["pitch"])


def hero_stores(prefix, paths=True):
    """Landing hero and final call to action: live stores lead with their official badges.
    While a store is pending, a working "Install today" button leads, a demo needs no phone and
    the stores still to come show their badges in a "Coming soon" frame. In the hero, one line
    per phone says how to get it: the store first, then the free way. The closing call to action
    (paths=False) shows the badges alone: the install section above it has said the rest."""
    stores = {s: store_of(s) for s in ("android", "ios")}
    live = [s for s in ("ios", "android") if stores[s]["status"] == "live"]  # Apple: App Store badge first
    btns = [store_button(stores[s], "", prefix) for s in live]
    if len(live) < 2:
        btns.insert(0, f'<a class="btn btn-primary" href="{prefix}#get">{t("nav.install")}</a>')
    out = '<div class="cta-row stores">\n        ' + "\n        ".join(btns) + "\n      </div>"
    pending = badge_row([stores[s] for s in ("ios", "android") if s not in live], prefix)
    if pending:
        out += "\n      " + pending
    if paths:
        out += ('\n      <ul class="install-paths">'
                f'<li>{svg(PARTS["android"]["glyph"])}<span><b>Android</b> {android_paths(prefix)}</span></li>'
                f'<li>{svg(PARTS["ios"]["glyph"])}<span><b>iPhone</b> {ios_paths(prefix)}</span></li>'
                '</ul>')
    return out


def hero_visual(prefix):
    """The landing hero's picture: the phone, the heartbeat line, and where the data lands. One
    destination, Home Assistant, drawn large enough to read; the others are named in the text.
    On a phone the desktop dashboard would be too small, so the same dashboard shows as Home
    Assistant draws it on a phone. Nothing overlaps at any width."""
    _, pw, ph, palt = IMAGES["A1-health"]
    _, ww, wh, walt = IMAGES["H6-health"]
    _, nw, nh, _ = IMAGES["H9-health-phone"]
    return f"""<div class="hero-visual">
      <figure class="hv-phone">
        <div class="phone"><img src="{prefix}img/A1-health.webp" alt="{t("hero.phone_alt")}" width="{pw}" height="{ph}" fetchpriority="high"></div>
        <figcaption><b>Life Dashboard Companion</b> <span>{t("strip.phone")}</span></figcaption>
      </figure>
      <svg class="hv-beat" viewBox="0 0 200 60" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
        <g fill="none" stroke-linecap="round" stroke-linejoin="round">
          <path class="beat-path" pathLength="100" d="M2 30 H62 L74 8 L90 52 L101 22 L109 30 H158"/>
          <circle class="beat-dot" cx="158" cy="30" r="5"/>
          <path class="arc a1" d="M172 20 A15 15 0 0 1 172 40"/>
          <path class="arc a2" d="M184 12 A27 27 0 0 1 184 48"/>
        </g>
      </svg>
      <figure class="hv-dest">
        <div class="hv-screen"><picture><source media="(max-width: 919px)" srcset="{prefix}img/H9-health-phone.webp" width="{nw}" height="{nh}"><img src="{prefix}img/H6-health.webp" alt="{walt}" width="{ww}" height="{wh}" fetchpriority="high"></picture></div>
        <figcaption><b>Home Assistant</b> <span>{t("strip.server")}</span></figcaption>
      </figure>
    </div>"""


GLOBE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><ellipse cx="12" cy="12" rx="4" ry="9"/></svg>'
MENU = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path class="m1" d="M4 7h16"/><path class="m2" d="M4 12h16"/><path class="m3" d="M4 17h16"/></svg>'


def lang_links(pid):
    """The same page in every language it exists in, as links. Empty while it has no translation."""
    langs = [c for c in LANGS if exists(pid, c)]
    if len(langs) < 2:
        return []
    return [f'<a href="=/{path_of(pid, c)}" lang="{LANGS[c]["hreflang"]}" hreflang="{LANGS[c]["hreflang"]}"'
            f'{" aria-current=\"true\"" if c == L else ""}>{LANGS[c]["name"]}</a>' for c in langs]


def lang_menu(pid):
    """The language menu in the header. A <details>, so it opens without a script."""
    links = lang_links(pid)
    if not links:
        return ""
    items = "".join(f"<li>{a}</li>" for a in links)
    # The button shows two letters. Its name comes from its own text, the full words hidden
    # before the letters, so the name always holds what is on the screen.
    short = LANGS[L]["hreflang"].split("-")[0].upper()
    return (f'<details class="lang-menu"><summary>{GLOBE}<span class="sr-only">{t("nav.language")}: {LANGS[L]["name"]}</span>'
            f'<span>{short}</span></summary><ul>{items}</ul></details>')


def lang_row(pid):
    """The same links once more in the footer, as plain text links."""
    links = lang_links(pid)
    if not links:
        return ""
    return f'<p class="lang-row">{GLOBE}<span class="sr-only">{t("nav.language")}:</span> {" ".join(links)}</p>'


def nav(prefix, active=None, pid=None):
    """The bar of every Life Dashboard page: the four parts and the guides, the language, GitHub
    and the install button. Below 1040px the links fold into a menu (a <details>, so it opens
    without a script) that also holds the dashboard cards, the languages and GitHub; the install
    button stays in the bar. pid: the page being written, for the language menu."""
    def a(href, label, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{href}"{cur}>{label}</a>'
    on_product = active in PARTS
    repo = {"ios": REPO_IOS, "home-assistant": REPO_HA, "grafana": REPO_STACK,
            "screen-time-card": REPO_ST_CARD, "sleep-card": REPO_CARD}.get(active, REPO)
    links = [
        a(f"{prefix}android/", "Android", "android"),
        a(f"{prefix}ios/", "iPhone", "ios"),
        a(f"{prefix}home-assistant/", PARTS["home-assistant"]["nav"], "home-assistant"),
        a(f"{prefix}grafana/", "Grafana", "grafana"),
        a(f"{prefix}guides/", t("nav.guides"), "guides"),
    ]
    # The menu also names the two dashboard cards, under Home Assistant: the bar has no room for them.
    panel = links[:3] + [a(f"{prefix}{c}/", PARTS[c]["name"], c).replace("<a ", '<a class="sub" ', 1) for c in CARDS] + links[3:]
    install = "#get" if on_product or active == "landing" else f"{prefix}#get"
    langs = lang_links(pid) if pid else []
    panel_langs = (f'\n          <p class="nav-panel-langs">{GLOBE}<span class="sr-only">{t("nav.language")}:</span> {" ".join(langs)}</p>'
                   if langs else "")
    return f"""<header class="nav has-menu">
  <div class="wrap">
    <a class="brand" href="{prefix}" aria-label="{t("nav.home")}">
      <img class="mark" src="{prefix}img/icon-96.webp" alt="" width="32" height="32">
      <span>Life Dashboard</span>
    </a>
    <nav class="nav-links" aria-label="{t("nav.main")}">
      {"\n      ".join(links)}
    </nav>
    <div class="nav-tools">
      {lang_menu(pid) if pid else ""}
      <a class="nav-icon" href="{repo}" aria-label="GitHub">{GH}</a>
      <a class="btn btn-primary btn-sm" href="{install}">{t("nav.install")}</a>
      <details class="nav-menu">
        <summary aria-label="{t("nav.menu")}">{MENU}</summary>
        <div class="nav-panel">
          <ul>
            {"\n            ".join(f"<li>{x}</li>" for x in panel)}
            <li><a href="{repo}">{GH} GitHub</a></li>
          </ul>{panel_langs}
        </div>
      </details>
    </div>
  </div>
</header>"""


# The guides the footer names; the guide index holds all of them.
FOOTER_GUIDES = ["health-connect-home-assistant", "apple-health-home-assistant", "samsung-health-home-assistant",
                 "fitbit-home-assistant", "health-connect-webhook"]


def footer(prefix, pid=None):
    """Three short columns, then one small line each for the legal links, the language and the
    imprint. Every guide is one click away through the index; the trademark notices and badge
    credits have a page of their own (/legal/)."""
    prods = "\n          ".join(f'<li><a href="{prefix}{s}/">{PARTS[s]["name"]}</a></li>' for s in PRODUCTS)
    guides = "\n          ".join(f'<li><a href="{prefix}{g}/">{GUIDE_NAMES[g]}</a></li>' for g in FOOTER_GUIDES)
    docs = [(f"{REPO}/blob/main/docs/usage.md", "android_setup"), (f"{REPO_IOS}/blob/main/docs/usage.md", "ios_setup"),
            (f"{REPO}/blob/main/docs/webhook.md", "payload"), (f"{prefix}feedback/", "feedback"),
            (f"{REPO}/blob/main/AI_POLICY.md", "ai_policy"),
            ("https://github.com/owen282000?tab=repositories&amp;q=life-dashboard", "repos")]
    doc_items = "\n          ".join(f'<li><a href="{h}">{t("footer.docs." + k)}</a></li>' for h, k in docs)
    legal = [(f"{REPO}/blob/main/PRIVACY.md", t("footer.docs.privacy_android")), (f"{prefix}ios/privacy/", t("footer.docs.privacy_ios")),
             ("/legal/", t("footer.legal"))]
    legal_items = "".join(f'<li><a href="{h}">{n}</a></li>' for h, n in legal)
    return f"""<footer class="footer">
  <div class="wrap">
    <div class="foot-top">
      <div class="foot-about">
        <a class="brand" href="{prefix}"><img class="mark" src="{prefix}img/icon-96.webp" alt="" width="32" height="32" loading="lazy"> <span>Life Dashboard</span></a>
        <p>{t("footer.about", discussions=f"{REPO}/discussions")}</p>
      </div>
      <div class="foot-col">
        <h2 class="foot-h">{t("footer.products")}</h2>
        <ul>
          {prods}
        </ul>
      </div>
      <div class="foot-col">
        <h2 class="foot-h">{t("footer.guides")}</h2>
        <ul>
          {guides}
          <li><a class="foot-all" href="{prefix}guides/">{t("footer.all_guides", n=len(GUIDES))}</a></li>
        </ul>
      </div>
      <div class="foot-col">
        <h2 class="foot-h">{t("footer.docs_title")}</h2>
        <ul>
          {doc_items}
        </ul>
      </div>
    </div>
    <div class="foot-bottom">
      <ul class="foot-legal">{legal_items}</ul>
      {lang_row(pid) if pid else ""}
      <p class="foot-note">{t("footer.imprint")}</p>
      <p class="foot-note">{t("footer.no_tracking")}</p>
    </div>
  </div>
</footer>"""


def small_footer(pid):
    """The footer of the developer page, the site's privacy notice and the legal page."""
    return f"""<footer class="footer small">
  <div class="wrap">
    <div class="foot-bottom">
      <ul class="foot-legal"><li><a href="/legal/">{t("footer.legal")}</a></li></ul>
      {lang_row(pid)}
      <p class="foot-note">{t("footer.imprint")}</p>
      <p class="foot-note">{t("hub.footer")} {t("footer.no_tracking")}</p>
    </div>
  </div>
</footer>"""


def small_nav(pid):
    return f"""<header class="nav">
  <div class="wrap">
    <a class="brand" href="/"><img class="mark" src="/img/ov-68.png" alt="" width="32" height="32"> <span>Owen Vogelaar</span></a>
    <div class="nav-tools">
      {lang_menu(pid)}
      <a class="nav-icon" href="https://github.com/owen282000" aria-label="GitHub">{GH}</a>
    </div>
  </div>
</header>"""


def head(pid, title, desc, og_type="website", og_title=None, ld=None, og_desc=None, og_image_alt=None, owner=False):
    """The <head> of a page in the language being built: a canonical to itself, an hreflang
    link to every language the page exists in (itself included) and x-default to English, and
    the Open Graph and Twitter tags in this language. owner: the developer page and the site's
    privacy notice, which carry Owen's mark instead of the app icon."""
    url = url_of(pid)
    ldtag = f'\n<script type="application/ld+json">\n{ld}\n</script>' if ld else ""
    hreflang = "".join(f'\n<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in alternates(pid))
    locales = f'\n<meta property="og:locale" content="{LANGS[L]["og_locale"]}">' + "".join(
        f'\n<meta property="og:locale:alternate" content="{LANGS[c]["og_locale"]}">' for c in LANGS if c != L and exists(pid, c))
    icons = ('<link rel="icon" href="/favicon.ico" sizes="48x48">\n<link rel="icon" type="image/png" sizes="32x32" href="/img/ov-32.png">\n'
             '<link rel="apple-touch-icon" href="/img/ov-180.png">' if owner else
             f'<link rel="icon" type="image/png" sizes="32x32" href="{LD}img/icon-32.png">\n<link rel="apple-touch-icon" href="{LD}img/icon-180.png">')
    image, iw, ih = (f"{DOMAIN}img/social.png", 1200, 630) if owner else (f"{BASE}img/social.png", 1280, 640)
    alt = html.escape(og_image_alt or t("og_image_alt"))
    og_t, og_d = html.escape(og_title or title), html.escape(og_desc or desc)
    site_name = "Owen Vogelaar" if owner else "Life Dashboard"
    return f"""<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">{hreflang}
<meta name="robots" content="max-image-preview:large">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#F7F9F8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#101418" media="(prefers-color-scheme: dark)">
{icons}
<link rel="stylesheet" href="{LD}site.css">
<meta property="og:type" content="{og_type}">{locales}
<meta property="og:site_name" content="{site_name}">
<meta property="og:title" content="{og_t}">
<meta property="og:description" content="{og_d}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="{iw}">
<meta property="og:image:height" content="{ih}">
<meta property="og:image:alt" content="{alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_t}">
<meta name="twitter:description" content="{og_d}">
<meta name="twitter:image" content="{image}">
<meta name="twitter:image:alt" content="{alt}">{ldtag}
</head>"""


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def tokens(s):
    """{{status:android}} and {{status:ios}} become the store sentences, {{play_url}} and
    {{app_store_url}} the links to the Play and App Store listings (with the page's campaign
    filled in when the page is written)."""
    return (s.replace("{{status:android}}", STATUS_TEXT["android"]).replace("{{status:ios}}", STATUS_TEXT["ios"])
            .replace("{{play_url}}", PLAY_LINK).replace("{{app_store_url}}", APP_STORE_LINK))


def image(name, prefix, cls="", eager=False):
    kind, w, h, alt = IMAGES[name]
    load = ' fetchpriority="high"' if eager else ' loading="lazy"'
    img = f'<img src="{prefix}img/{name}.webp" alt="{alt}" width="{w}" height="{h}"{load}>'
    if name in PHONE_SHOT:
        ph, pw, phh = PHONE_SHOT[name], IMAGES[PHONE_SHOT[name]][1], IMAGES[PHONE_SHOT[name]][2]
        img = (f'<picture><source media="(max-width: 520px)" srcset="{prefix}img/{ph}.webp" width="{pw}" height="{phh}">{img}</picture>')
    if kind == "phone":
        cls = f"{cls} cut".strip() if name in CUT else cls
        return f'<div class="{f"phone {cls}".strip()}">{img}</div>'
    if kind == "card":
        return f'<figure class="{f"qr-card {cls}".strip()}">{img}</figure>'
    return (f'<div class="{f"wide-shot {cls}".strip()}">'
            f'<a class="shot-link" href="{prefix}img/{name}.webp" aria-label="{alt}, {t("full_size")}">{img}</a></div>')


def faq_entity(qa):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]}


def breadcrumb(*crumbs):
    """crumbs: (name, address) from the top down; the developer page leads every trail."""
    crumbs = (("Owen Vogelaar", url_of("hub")),) + crumbs
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs, 1)]}


def ld_json(graph):
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False)


def page(head_html, body, comment):
    m = LANGS[L]
    return f"""<!DOCTYPE html>
<!-- {comment} Generated by tools/site/build.py: edit the source there, not this file. -->
<html lang="{m["hreflang"]}">
{head_html}
<body>
<a class="skip" href="#main">{t("skip")}</a>

{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------------------------
# Guides: one template for every guide in every language.
#
# A guide is i18n/<lang>/guides/<id>.html: a header comment (title, description, updated, and
# for a translation optionally slug), then plain HTML: one <h1>, the introduction, <h2> sections,
# and a <section class="faq"> of <details>. The template adds the rest: the breadcrumb, the
# byline with the date and reading time, the first button, "On this page" from the <h2>s, ids on
# the headings, accessible tables and code blocks, figures for the <!-- IMG: ... (name.png) -->
# placeholders, the closing panel with the store buttons, related guides and the JSON-LD.
# Components a guide can use: <ol> for steps, <p class="note">, <p class="tip"> and
# <p class="warn"> for callouts, <p class="flow-line"> with <span>s for a chain of apps,
# <table>, <pre><code>, <details> inside the FAQ.

PURPLE = {"A4-screen-time", "H7-screen-time", "T1-screen-time-cards", "T2-screen-time-card-phone",
          "T3-screen-time-week", "T4-screen-time-family"}
IMG_MARK = r"<!--\s*IMG:[^>]*?\(?(ios-[a-z]+|[A-Za-z]\d?-[a-z-]+)(?:\.png|\.webp)?\)?[^>]*-->"


def figure(m):
    name = m.group(1)
    kind, w, h, alt = IMAGES[name]
    full = f'{alt}, {t("full_size")}'
    tone = " purple" if name in PURPLE else ""
    if kind == "phone":
        return f'<figure class="shot{tone}"><a class="shot-link" href="{LD}img/{name}.webp" aria-label="{full}">{image(name, LD)}</a></figure>'
    if kind == "diagram":
        # A drawn diagram brings its own card and text, so it gets the full column, without a frame.
        return (f'<figure class="diagram"><a class="shot-link" href="{LD}img/{name}.webp" aria-label="{full}">'
                f'<img src="{LD}img/{name}.webp" alt="{alt}" width="{w}" height="{h}" loading="lazy"></a></figure>')
    # A card (the QR dialog) stays narrow; a wide screenshot, such as a dashboard, gets the full column.
    size = " full" if kind == "wide" else ""
    note = f'<figcaption>{CAPTIONS[name]}</figcaption>' if name in CAPTIONS else ""
    captioned = " captioned" if note else ""
    return (f'<figure class="shot wide{size}{captioned}"><a class="shot-link" href="{LD}img/{name}.webp" aria-label="{full}">'
            f'<img src="{LD}img/{name}.webp" alt="{alt}" width="{w}" height="{h}" loading="lazy"></a>{note}</figure>')


def slugify(text):
    text = strip_tags(text).lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


HEADING = re.compile(r"<(h[23])>(.*?)</\1>", re.S)


def heading_ids(body):
    return [slugify(m.group(2)) for m in HEADING.finditer(body)]


def enhance(body, ids=None):
    """Accessible tables and code blocks, ids on headings, the guide FAQ heading. ids: the
    heading ids of the English guide. A translation with the same headings in the same order
    takes them over, so #set-it-up is the same section in every language and a link with a
    fragment keeps working; a guide with headings of its own gets ids from its own words."""
    def table(m):
        caps = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", body[:m.start()], re.S)
        label = strip_tags(caps[-1]) if caps else t("table")
        tb = m.group(0)
        tb = re.sub(r"<th></th>", f'<th scope="col">{t("feature")}</th>', tb)
        tb = re.sub(r"<thead>(.*?)</thead>", lambda x: "<thead>" + x.group(1).replace("<th>", '<th scope="col">') + "</thead>", tb, flags=re.S)
        tb = re.sub(r"(<tbody>.*?</tbody>)", lambda x: re.sub(r"<tr>\s*<td>(.*?)</td>", r'<tr><th scope="row">\1</th>', x.group(1), flags=re.S), tb, flags=re.S)
        # A cell that holds a link and nothing else gets a finger-sized link on a phone
        # (td.only-link in site.css); a link inside a sentence stays part of the sentence.
        tb = re.sub(r"<td>(\s*<a\b[^>]*>[^<]*</a>\s*)</td>", r'<td class="only-link">\1</td>', tb)
        return f'<div class="table-wrap" tabindex="0" role="region" aria-label="{html.escape(label)}">{tb}</div>'
    body = re.sub(r"<table>.*?</table>", table, body, flags=re.S)

    def pre(m):
        # A focusable code block needs a name: "Code: <the heading it sits under>".
        caps = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", body[:m.start()], re.S)
        label = t("code", name=strip_tags(caps[-1]) if caps else t("code_example"))
        return f'<pre tabindex="0" role="region" aria-label="{html.escape(label)}"><code>'
    body = re.sub(r"<pre><code>", pre, body)
    own = heading_ids(body)
    use = iter(ids if ids and len(ids) == len(own) else own)
    body = HEADING.sub(lambda m: f'<{m.group(1)} id="{next(use)}">{m.group(2)}</{m.group(1)}>', body)
    return re.sub(r'(<h2 id="faq">)FAQ(</h2>)', lambda m: m.group(1) + t("faq") + m.group(2), body)


def guide_source(pid, lang):
    return tokens(source(pid, lang).read_text())


def guide_apps(pid, about):
    """Which app a guide leads with: the iPhone guides the iPhone app, a guide about both phones
    both stores, Android first; every other guide the Android app."""
    if pid in dict(GROUPS)["iphone"]:
        return ["ios"]
    return ["android", "ios"] if "#ios" in about else ["android"]


def store_block(app):
    """A store badge with its price line and the other routes, for the closing panel."""
    lead = lead_item(app)
    rest = [it for it in PARTS[app]["get"] if it is not lead]
    alt = f'<p class="aside-alt">{alt_links(rest, LD)}</p>'
    if free_follows(app, lead):
        alt = (f'<p class="aside-alt">{lead["pitch"]}</p>\n        '
               f'<p class="aside-alt">{PARTS[app]["free_line"]} {alt_links(rest, LD)}</p>')
    elif lead.get("pitch"):
        alt = f'<p class="aside-alt">{lead["pitch"]}</p>\n        {alt}'
    return f'<div class="panel-store">{lead_button(lead, LD)}\n        {alt}</div>'


def related_guides(pid):
    """Up to three guides from the same group, as cards, and a link to all of them."""
    group = next(slugs for _, slugs in GROUPS if pid in slugs)
    cards = "\n      ".join(guide_card(g, LD) for g in [g for g in group if g != pid][:3])
    return f"""<section class="section tight related band" aria-labelledby="related">
  <div class="wrap">
    <div class="section-head split"><h2 id="related">{t("guide.related")}</h2><a class="link-arrow" href="{LD}guides/">{t("guide.all")}</a></div>
    <ul class="guide-list three">
      {cards}
    </ul>
  </div>
</section>"""


def build_guide(pid):
    lang = L
    src = guide_source(pid, lang)
    title, desc = meta(src, "title"), meta(src, "description")
    updated = opt_meta(src, "updated") or UPDATED
    published = opt_meta(src, "published") or UPDATED
    PAGE_DATES[(pid, lang)] = updated
    about = ["#" + a.strip().lstrip("#") for a in opt_meta(src, "about").split(",")] if opt_meta(src, "about") else GUIDE_ABOUT[pid]
    crumb = GUIDE_NAMES[pid]
    body = body_of(src)
    body = re.sub(IMG_MARK, figure, body)
    body = re.sub(r"</li>(\s*)(<figure\b.*?</figure>)", r"\1\2</li>", body, flags=re.S)
    ids = heading_ids(body_of(guide_source(pid, "en"))) if lang != "en" else None
    body = enhance(body, ids)
    h1_html = re.search(r"<h1>(.*?)</h1>", body, re.S).group(1)
    h1 = strip_tags(h1_html)
    after = body[body.index("</h1>") + 5:]
    cut_at = after.index("<h2") if "<h2" in after else len(after)
    intro, rest = after[:cut_at].strip(), after[cut_at:].strip()
    toc = "\n        ".join(f'<li><a href="#{i}">{strip_tags(x)}</a></li>' for i, x in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', rest, re.S))
    minutes = max(1, round(len(strip_tags(body).split()) / 220))
    text, buttons = NEXT[pid]
    btns = "\n      ".join(f'<a class="btn {c}" href="{h}">{label}</a>' for c, h, label in buttons)
    apps = guide_apps(pid, about)
    if len(apps) == 2:
        aside = t("guide.aside_both")
    else:
        aside = t("guide.aside_" + apps[0])
    panel = f"""<section class="get-panel" aria-labelledby="get-the-app">
      <h2 id="get-the-app">Life Dashboard Companion</h2>
      <p>{text}</p>
      <div class="stores">
        {"".join(store_block(a) for a in apps)}
      </div>
      <p class="panel-btns">
      {btns}
      </p>
      <p class="panel-note">{aside}</p>
    </section>"""
    if '<section class="faq">' in rest:
        rest = rest.replace('<section class="faq">', panel + '\n\n<section class="faq">', 1)
    else:
        rest += "\n\n" + panel
    first = buttons[0]
    qa = [(strip_tags(q), strip_tags(a)) for q, a in re.findall(r"<summary>(.*?)</summary>\s*(.*?)</details>", rest, re.S)]
    url = url_of(pid)
    graph = [
        {"@type": "TechArticle", "@id": url + "#article", "headline": h1, "description": desc, "url": url,
         "mainEntityOfPage": url, "inLanguage": LANGS[lang]["hreflang"],
         "author": {"@id": f"{BASE}#owen"}, "publisher": {"@id": f"{DOMAIN}#org"},
         "about": [{"@type": "SoftwareApplication", "@id": f"{BASE}{i}", "name": ENTITY_NAME[i]} for i in about],
         "datePublished": published, "dateModified": updated, "image": f"{BASE}img/social.png",
         "timeRequired": f"PT{minutes}M", "isPartOf": {"@id": f"{BASE}#website"}},
        breadcrumb(("Life Dashboard", url_of("landing")), (t("nav.guides"), url_of("guides") if exists("guides", lang) else url_of("guides", "en")), (crumb, url)),
        ME, ORG, WEBSITE,
    ]
    graph += [ENTITIES[c] for c in CARDS if ENTITY_ID[c] in about]
    if qa:
        graph.append(faq_entity(qa))
    main = f"""{nav(LD, "guides", pid)}

<main id="main" class="guide">
  <header class="guide-head">
    <div class="wrap">
      <nav class="crumbs" aria-label="{t("breadcrumb")}"><a href="{LD}">Life Dashboard</a><span aria-hidden="true">/</span><a href="{LD}guides/">{t("nav.guides")}</a><span aria-hidden="true">/</span><span aria-current="page">{crumb}</span></nav>
      <h1>{h1_html}</h1>
      <div class="guide-intro">
{intro}
      </div>
      <p class="guide-meta"><span>{t("guide.byline")}</span> <span><time datetime="{updated}">{t("guide.updated", date=date_text(updated))}</time></span> <span>{t("guide.read_time", n=minutes)}</span></p>
      <p class="guide-cta"><a class="btn btn-primary" href="{first[1]}">{first[2]}</a></p>
    </div>
  </header>
  <div class="wrap guide-grid">
    <nav class="toc" aria-labelledby="toc-title">
      <h2 id="toc-title">{t("guide.toc")}</h2>
      <ol>
        {toc}
      </ol>
    </nav>
    <article class="prose">
{rest}
    </article>
  </div>
  {related_guides(pid)}
</main>

{footer(LD, pid)}"""
    head_html = head(pid, title, desc, "article", h1, ld_json(graph))
    emit(pid, lang, page(head_html, main, "Guide page of the Life Dashboard site."))
    return f"guide {pid}: title {len(title)}, description {len(desc)}, faqs {len(qa)}"


def guide_card(g, prefix, compact=False):
    slug, name, tag, desc = next(x for x in GUIDES if x[0] == g)
    if compact:
        return f'<li><a class="guide-link" href="{prefix}{slug}/">{name}</a></li>'
    # A row, not a card: the name is the link, the line under it says what the guide covers.
    return f'<li><a href="{prefix}{slug}/"><b>{name}</b><span>{desc}</span></a></li>'


def guide_groups(prefix):
    """The landing page's guides, under a few real headings instead of a tag per card."""
    listed = [s for _, slugs in GUIDE_GROUPS for s in slugs]
    missing = [g[0] for g in GUIDES if g[0] not in listed]
    assert not missing and len(listed) == len(set(listed)), f"GROUPS: missing {missing} or a guide listed twice"
    cols = []
    for title, slugs in GUIDE_GROUPS:
        items = "".join(guide_card(s, prefix, compact=True) for s in slugs if s in GUIDE_NAMES)
        cols.append(f'<div class="guide-group"><h3>{title}</h3><ul>{items}</ul></div>')
    return '<div class="guide-groups">\n      ' + "\n      ".join(cols) + "\n    </div>"


def build_index():
    """/life-dashboard/guides/: every guide with its one-line description, under the same groups
    as on the landing page. Made from strings.json alone."""
    pid = "guides"
    title, desc = t("index.title"), t("index.description")
    PAGE_DATES[(pid, L)] = max(d for (p, l), d in PAGE_DATES.items() if p in GUIDE_IDS and l == L) if any(
        p in GUIDE_IDS and l == L for p, l in PAGE_DATES) else UPDATED
    groups = []
    for (key, slugs), (name, _) in zip(GROUPS, GUIDE_GROUPS):
        cards = "\n        ".join(guide_card(g, LD) for g in slugs)
        groups.append(f"""<section class="index-group" aria-labelledby="g-{key}">
      <h2 id="g-{key}">{name}</h2>
      <ul class="guide-list">
        {cards}
      </ul>
    </section>""")
    url = url_of(pid)
    graph = [{"@type": "CollectionPage", "@id": url, "url": url, "name": title, "description": desc,
              "inLanguage": LANGS[L]["hreflang"], "isPartOf": {"@id": f"{BASE}#website"},
              "mainEntity": {"@type": "ItemList", "itemListElement": [
                  {"@type": "ListItem", "position": i, "name": g[1], "url": url_of(g[0]) if exists(g[0], L) else url_of(g[0], "en")}
                  for i, g in enumerate(GUIDES, 1)]}},
             breadcrumb(("Life Dashboard", url_of("landing")), (t("nav.guides"), url)), ME, ORG, WEBSITE]
    main = f"""{nav(LD, "guides", pid)}

<main id="main" class="guide">
  <header class="guide-head index-head">
    <div class="wrap">
      <nav class="crumbs" aria-label="{t("breadcrumb")}"><a href="{LD}">Life Dashboard</a><span aria-hidden="true">/</span><span aria-current="page">{t("nav.guides")}</span></nav>
      <h1>{t("index.h1")}</h1>
      <div class="guide-intro"><p>{t("index.lead")}</p></div>
    </div>
  </header>
  <div class="wrap index-groups">
    {"".join(groups)}
  </div>
</main>

{footer(LD, pid)}"""
    emit(pid, L, page(head(pid, title, desc, "website", t("index.h1"), ld_json(graph)), main, "The guide index of the Life Dashboard site."))
    return f"index: {len(GUIDES)} guides"

# ---------------------------------------------------------------------------------------------
# Products: i18n/<lang>/products/<slug>.json, one template.

def build_product(slug):
    d = json.loads(tokens(source(slug, L).read_text()))
    # The ids of the sections come from the English page, so #get, #building and the like are
    # the same in every language.
    den = json.loads(source(slug, "en").read_text())
    kickers = [x["kicker"] for x in (den if len(den["sections"]) == len(d["sections"]) else d)["sections"]]
    p = PARTS[slug]
    url = url_of(slug)
    prefix = LD
    lead = lead_item(slug)
    rest = [it for it in p["get"] if it is not lead]
    hero_kind = IMAGES[d["hero_image"]][0]
    # The first highlight is what the part is for, so it gets the large cell; the rest follow
    # as a plain list, as many as the JSON holds.
    hl = d["highlights"]
    highlights = (f'<div class="hl-lead"><h3>{html.escape(hl[0]["title"])}</h3><p>{html.escape(hl[0]["text"])}</p></div>'
                  + '\n        <ul class="hl-list">' + "".join(
                      f'<li><h3>{html.escape(h["title"])}</h3><p>{html.escape(h["text"])}</p></li>' for h in hl[1:]) + '</ul>')
    rows = []
    # Rhythm: text and picture alternate sides. A wide screenshot (a dashboard) gets a full-width
    # row under its text, so it is large enough to read; a phone is never stretched over one.
    for i, s in enumerate(d["sections"]):
        bullets = "\n          ".join(
            f'<li>{b["main"]}' + (f' <span>{b["sub"]}</span>' if b.get("sub") else "") + "</li>" for b in s["bullets"])
        stack = False
        if s.get("code"):
            # A section can show a code window instead of a screenshot.
            tone = ""
            title = html.escape(s["code"]["title"])
            media = (f'<div class="show-code"><div class="code-window"><div class="code-bar"><span>{title}</span></div>'
                     f'<pre tabindex="0" role="region" aria-label="{title}"><code>{html.escape(s["code"]["code"])}</code></pre></div></div>')
        else:
            kind = IMAGES[s["image"]][0]
            stack = kind == "wide"
            tone = " purple" if s["image"] in PURPLE else ""
            shape = " is-wide" if kind == "wide" else " has-card" if kind == "card" else " two" if s.get("image2") else ""
            media = (f'<div class="show-media stage{tone}{shape}">'
                     + (f'{image(s["image"], prefix)}{image(s["image2"], prefix)}' if s.get("image2") else image(s["image"], prefix))
                     + (f'<p class="shot-note">{CAPTIONS[s["image"]]}</p>' if s["image"] in CAPTIONS else "")
                     + '</div>')
        link = f'<a class="link-arrow" href="{s["link"]["href"]}">{html.escape(s["link"]["text"])}</a>' if s.get("link") else ""
        # Only the screen time label carries meaning (purple means screen time); the others
        # repeated their heading and are gone. The id stays, since links point at it.
        label = f'<p class="label{tone}">{html.escape(s["kicker"])}</p>\n        ' if tone else ""
        h2 = s["h2"].replace("QR code", "QR&nbsp;code")
        body = f"""<p>{s["text"]}</p>
        <ul class="ticks{" purple-ticks" if tone else ""}">
          {bullets}
        </ul>
        {link}"""
        if stack:
            rows.append(f"""<div class="show stack" id="{slugify(kickers[i])}">
      <div class="stack-text">
        <div>{label}<h2>{h2}</h2></div>
        <div>{body}</div>
      </div>
      {media}
    </div>""")
            continue
        rows.append(f"""<div class="show{" flip" if i % 2 else ""}" id="{slugify(kickers[i])}">
      {media}
      <div>
        {label}<h2>{h2}</h2>
        {body}
      </div>
    </div>""")
    faq = "\n      ".join(f'<details{" id=" + chr(34) + f["id"] + chr(34) if f.get("id") else ""}{" open" if f.get("open") else ""}>\n        <summary>{html.escape(f["q"])}</summary>\n        <p>{f["a"]}</p>\n      </details>' for f in d["faq"])
    gl = d.get("guides", [])
    guides = "\n      ".join(guide_card(g, prefix) for g in gl)
    single_label = t("product.single_" + slug) if slug in ("ios", "grafana") else t("product.single")
    single_guide = (f'<p class="faq-more">{single_label}: <a class="link-arrow" href="{LD}{gl[0]}/">{GUIDE_NAMES[gl[0]]}</a></p>' if len(gl) == 1 else "")
    is_card = slug in CARDS
    others = CARD_SIBLINGS[slug] if is_card else [s for s in ORDER if s != slug]
    siblings = "\n      ".join(part_link(s) for s in others)
    family_cls = "family three" if len(others) == 3 else "family"
    others_title, others_text = (t("product.others_card"), t("product.others_card_text")) if is_card else (t("product.others"), t("product.others_text"))
    # The integration's page also names the two cards that draw its sensors.
    more_cards = "\n    " + cards_block(prefix, "family-cards") if slug == "home-assistant" else ""
    works_with = t("product.works_with_" + ("app" if slug in ("android", "ios") else slug))
    # Listings elsewhere, each with its badge saved in img/badges/ like the store badges.
    listed = {
        "android": f'<p class="listed badges"><a class="badge-link" href="https://alternativeto.net/software/life-dashboard-companion/about/"><img class="badge-img" src="{LD}img/badges/alternativeto.svg" alt="{t("product.alternativeto")}" width="229" height="77" loading="lazy"></a></p>',
    }.get(slug, "")
    entity = ENTITIES[slug]
    compare = ""
    if d.get("compare"):
        c = d["compare"]
        chead = "".join(f'<th scope="col">{h or t("feature")}</th>' for h in c["head"])
        cbody = "".join("<tr><th scope=\"row\">" + r[0] + "</th>" + "".join(f"<td>{x}</td>" for x in r[1:]) + "</tr>" for r in c["rows"])
        compare = f"""<section class="section tight" id="compare">
  <div class="wrap">
    <div class="section-head"><h2>{c["title"]}</h2><p>{c["intro"]}</p></div>
    <div class="table-wrap compare-wrap" tabindex="0" role="region" aria-label="{html.escape(c["title"])}"><table class="compare"><thead><tr>{chead}</tr></thead><tbody>{cbody}</tbody></table></div>
    <p class="fineprint">{c["source"]}</p>
  </div>
</section>

"""
    commands = ""
    if d.get("commands"):
        ctitle = html.escape(d["commands"]["title"])
        commands = (f'<div class="code-window"><div class="code-bar"><span>{ctitle}</span></div>'
                    f'<pre tabindex="0" role="region" aria-label="{ctitle}"><code>{html.escape(d["commands"]["code"])}</code></pre></div>'
                    f'<p class="fineprint">{d["commands"]["after"]}</p>')
    graph = [breadcrumb(("Life Dashboard", url_of("landing")), (d["nav_name"], url)),
             {"@type": "WebPage", "@id": url, "url": url, "name": d["title"], "description": d["description"],
              "about": {"@id": f"{BASE}{ENTITY_ID[slug]}"}, "mainEntity": entity,
              "isPartOf": {"@id": f"{BASE}#website"}, "inLanguage": LANGS[L]["hreflang"], "dateModified": d.get("updated", UPDATED)},
             faq_entity([(f["q"], strip_tags(f["a"])) for f in d["faq"]]), ME, ORG, WEBSITE,
             {k: v for k, v in PROJECT.items() if k != "hasPart"}]
    PAGE_DATES[(slug, L)] = d.get("updated", UPDATED)
    guides_section = f"""<section class="section tight band">
  <div class="wrap split">
    <div class="section-head"><h2>{t("product.guides")}</h2></div>
    <ul class="guide-list two">
      {guides}
    </ul>
  </div>
</section>
""" if len(gl) > 1 else ""
    faq_title = t("product.faq_" + slug)
    plain = [it for it in rest if not has_badge(it)]
    hero_alt = f'<p class="fineprint">{alt_links(plain, prefix)}</p>' if plain else ""
    if lead.get("pitch") and not free_follows(slug, lead):
        # The App Store: its price under the badge, then the other route.
        hero_alt = f'<p class="fineprint">{lead["pitch"]}</p>\n      {hero_alt}'
    # A badge-led part (HACS, Docker Compose) shows its badges in one row; the apps keep their
    # plain primary button with the store badges under it.
    hero_top = (badge_row([lead] + rest, prefix) if lead.get("kind") == "store" and has_badge(lead) else
                f'<div class="cta-row stores">\n        {lead_button(lead, prefix)}\n      </div>\n      {badge_row(rest, prefix)}')
    if free_follows(slug, lead):
        # Android: Google Play leads, its price and why under it, then the free routes.
        hero_top = (f'<div class="cta-row stores">\n        {badge(lead, prefix)}\n      </div>\n      '
                    f'<p class="fineprint">{lead["pitch"]} {p["free_line"]}</p>\n      {badge_row(rest, prefix)}')
    main = f"""{nav(prefix, slug, slug)}

<main id="main">

<section class="hero product-hero">
  <div class="wrap">
    <div class="hero-copy">
      <nav class="crumbs" aria-label="{t("breadcrumb")}"><a href="{LD}">Life Dashboard</a><span aria-hidden="true">/</span><span aria-current="page">{d["nav_name"]}</span></nav>
      <h1>{html.escape(d["h1"])}</h1>
      <p class="lead">{html.escape(d["lead"])}</p>
      {hero_top}
      {hero_alt}
      {repo_stats(slug)}
    </div>
    <div class="product-visual stage{" purple" if d["hero_image"] in PURPLE else ""}{" is-wide" if hero_kind == "wide" else " has-card" if hero_kind == "card" else ""}">
      {image(d["hero_image"], prefix, eager=True)}
    </div>
  </div>
</section>

<section class="section tight band">
  <div class="wrap">
    <h2 class="sr-only">{t("product.what")}</h2>
    <div class="highlights">
        {highlights}
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    {"".join(rows)}
  </div>
</section>

{compare}<section class="section tight band" id="get">
  <div class="wrap">
    <div class="section-head">
      <h2>{p["get_title"]}</h2>
    </div>
    <div class="get-split">
      {get_card(slug, prefix, req=False)}
      <div class="get-side">
        <h3>{t("product.need")}</h3>
        <p>{d["requirements"]}</p>
        <p class="fineprint">{works_with}</p>
        {commands}
        {listed}
      </div>
    </div>
  </div>
</section>

<section class="section tight" id="faq">
  <div class="wrap split">
    <div class="section-head">
      <h2>{faq_title}</h2>
    </div>
    <div>
      <div class="faq">
      {faq}
      </div>
      {single_guide}
    </div>
  </div>
</section>

{guides_section}
<section class="section tight">
  <div class="wrap">
    <div class="section-head"><h2>{others_title}</h2><p>{others_text}</p></div>
    <div class="{family_cls}">
      {siblings}
    </div>{more_cards}
  </div>
</section>

</main>

{footer(prefix, slug)}"""
    emit(slug, L, page(head(slug, d["title"], d["description"], "website", d["h1"], ld_json(graph)), main, f"Product page: {ENTITY_BASE[slug]['name']}."))
    return f"product {slug}: title {len(d['title'])}, description {len(d['description'])}, faqs {len(d['faq'])}"


# ---------------------------------------------------------------------------------------------
# Landing page, the developer page, privacy, llms.txt, sitemap, checks

def fill(src, name, content):
    pat = re.compile(rf"(<!-- BUILD:{name} -->).*?(<!-- /BUILD:{name} -->)", re.S)
    new, n = pat.subn(lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}", src)
    assert n >= 1, f"marker {name} not found"
    return new


# Projects that build on the payload; what each one is, in proof.projects.<name> of strings.json.
PROOF_PROJECTS = [
    ("Health Assistant", "https://github.com/health-assistant-io/health-assistant"),
    ("HealthQuery", "https://github.com/nikira-studio/healthquery"),
    ("fitbridge", "https://github.com/x-senpai-x/fitbridge"),
]
# Update when it changes; the numbers are floors, so they stay true.
PROOF_FLOORS = [("45+", "releases"), ("5", "outside"), ("4", "parts")]


def load_stats():
    """The numbers from stats.py, or None when there are none from the last week."""
    try:
        s = json.loads((HERE / "stats.json").read_text())
    except (OSError, ValueError):
        return None
    return s if time.time() - s.get("fetched", 0) < 7 * 86400 else None


STATS = load_stats()


def repo_stats(slug):
    """Stars, forks and contributors of one part's repo, under its hero. A zero is left out."""
    s = STATS and STATS["repos"].get(slug)
    if not s:
        return ""
    items = ", ".join(f"<b>{s[k]}</b> {t(f'stats.{k}_one') if s[k] == 1 else t(f'stats.{k}')}"
                      for k in ("stars", "forks", "contributors") if s[k])
    use = ""
    if s.get("active"):
        use = " " + t("stats.active", n=s["active"])
    elif s.get("downloads") and slug == "home-assistant":
        use = " " + t("stats.downloads_ha", n=s["downloads"])
    elif s.get("downloads") and slug == "grafana":
        use = " " + t("stats.downloads_stack", n=s["downloads"])
    return (f'<p class="repo-stats"><a href="https://github.com/{s["repo"]}">{t("stats.on_github")}</a>: {items}.{use} '
            f'<span>{t("stats.hourly")}</span></p>')


def proof_section():
    facts = [(n, S(f"proof.facts.{k}")) for n, k in PROOF_FLOORS]
    if STATS:
        facts = [(STATS["stars"], t("proof.stars")), (STATS["contributors"], t("proof.contributors")),
                 (STATS["repos"]["android"]["releases"], S("proof.facts.releases")), facts[2]]
    note = f'\n    <p class="stats-note">{t("proof.live")}</p>' if STATS else ""
    facts = "".join(f"<li><b>{n}</b> <span>{text}</span></li>" for n, text in facts)
    cards = "\n      ".join(
        f'<a class="part proj" href="{u}"><h3>{n}</h3><p>{S("proof.projects." + n)}</p><span class="go">{t("stats.on_github")}</span></a>'
        for n, u in PROOF_PROJECTS)
    cards += (f'\n      <a class="part proj-cta" href="{REPO}/discussions"><h3>{t("proof.yours_title")}</h3>'
              f'<p>{t("proof.yours_text")}</p><span class="go">{t("proof.yours_go")}</span></a>')
    return f"""<div class="section-head">
      <h2>{t("proof.title")}</h2>
    </div>
    <ul class="proof-facts">{facts}</ul>{note}
    <div class="family">
      {cards}
    </div>"""


def page_source(pid):
    return tokens(source(pid, L).read_text())


def build_landing():
    pid = "landing"
    raw = page_source(pid)
    src = body_of(raw)
    PAGE_DATES[(pid, L)] = opt_meta(raw, "updated") or UPDATED
    src = fill(src, "proof", proof_section())
    src = fill(src, "guides", guide_groups(LD))
    src = fill(src, "hero-stores", hero_stores(LD))
    src = fill(src, "hero-visual", hero_visual(LD))
    src = fill(src, "final-stores", hero_stores(LD, paths=False))
    src = fill(src, "get", get_section(LD))
    if "<!-- BUILD:faq-get -->" in src:
        src = fill(src, "faq-get", f"<p>{t('landing.faq_get', android=STATUS_TEXT['android'], ios=STATUS_TEXT['ios'])}</p>")
    faq = src[src.index('id="faq"'):]
    qa = [(strip_tags(q), strip_tags(a)) for q, a in re.findall(r"<summary>(.*?)</summary>\s*(.*?)</details>", faq, re.S)]
    graph = [WEBSITE, ME, ORG, PROJECT] + [ENTITIES[s] for s in PRODUCTS] + [SOURCE_CODE, faq_entity(qa),
                                                                             breadcrumb(("Life Dashboard", url_of(pid)))]
    main = f"""{nav(LD, "landing", pid)}

<main id="main">
{src.strip()}
</main>

{footer(LD, pid)}"""
    head_html = head(pid, meta(raw, "title"), meta(raw, "description"), "website", opt_meta(raw, "og_title"), ld_json(graph),
                     opt_meta(raw, "og_description"), opt_meta(raw, "og_image_alt"))
    emit(pid, L, page(head_html, main, "Landing page of Life Dashboard."))
    return f"landing: faqs {len(qa)}"


def build_hub():
    """The domain root: the developer page, with a card per product."""
    pid = "hub"
    raw = page_source(pid)
    PAGE_DATES[(pid, L)] = opt_meta(raw, "updated") or UPDATED
    url = url_of(pid)
    graph = [{"@type": "WebSite", "@id": f"{DOMAIN}#website", "url": DOMAIN, "name": "Owen Vogelaar",
              "inLanguage": [m["hreflang"] for m in LANGS.values()], "publisher": {"@id": f"{DOMAIN}#org"}},
             {"@type": "ProfilePage", "@id": url, "url": url, "name": meta(raw, "title"), "inLanguage": LANGS[L]["hreflang"],
              "mainEntity": {"@id": f"{BASE}#owen"}, "isPartOf": {"@id": f"{DOMAIN}#website"}},
             ME, ORG,
             {"@type": "ItemList", "name": t("hub.list"), "itemListElement": [
                 {"@type": "ListItem", "position": 1, "url": url_of("landing") if exists("landing", L) else url_of("landing", "en"), "name": "Life Dashboard"}]}]
    main = f"""{small_nav(pid)}

<main id="main">
{body_of(raw).strip()}
</main>

{small_footer(pid)}"""
    head_html = head(pid, meta(raw, "title"), meta(raw, "description"), "website", opt_meta(raw, "og_title"), ld_json(graph),
                     opt_meta(raw, "og_description"), opt_meta(raw, "og_image_alt") or t("hub.og_image_alt"), owner=True)
    emit(pid, L, page(head_html, main, "The root of owen282000.com: a small developer page with a card per product."))
    return "hub"


def build_privacy():
    """The privacy notice of the website itself."""
    pid = "privacy"
    raw = page_source(pid)
    updated = opt_meta(raw, "updated") or UPDATED
    PAGE_DATES[(pid, L)] = updated
    url = url_of(pid)
    graph = [{"@type": "WebPage", "@id": url, "url": url, "name": meta(raw, "title"), "inLanguage": LANGS[L]["hreflang"],
              "dateModified": updated, "isPartOf": {"@id": f"{DOMAIN}#website"}, "publisher": {"@id": f"{DOMAIN}#org"}}, ORG]
    main = f"""{small_nav(pid)}

<main id="main" class="wrap plain-page">
  <article class="prose">
{body_of(raw).strip()}
    <p class="byline"><time datetime="{updated}">{t("last_updated", date=date_text(updated))}</time></p>
  </article>
</main>

{small_footer(pid)}"""
    head_html = head(pid, meta(raw, "title"), meta(raw, "description"), "website", None, ld_json(graph), owner=True)
    emit(pid, L, page(head_html, main, "Privacy notice for the website owen282000.com itself. The apps have their own policies."))
    return "privacy"


def build_legal():
    """/legal/: the trademark notices, the badge credits and the imprint, which used to fill the
    footer of every page. Made from strings.json alone, like the guide index."""
    pid = "legal"
    updated = "2026-11-20"
    PAGE_DATES[(pid, L)] = updated
    url = url_of(pid)
    title, desc = t("legal.title"), t("legal.description")
    graph = [{"@type": "WebPage", "@id": url, "url": url, "name": title, "inLanguage": LANGS[L]["hreflang"],
              "dateModified": updated, "isPartOf": {"@id": f"{DOMAIN}#website"}, "publisher": {"@id": f"{DOMAIN}#org"}}, ORG]
    main = f"""{small_nav(pid)}

<main id="main" class="wrap plain-page">
  <article class="prose">
    <h1>{t("legal.h1")}</h1>
    <p>{t("legal.intro")}</p>
    <h2 id="trademarks">{t("legal.trademarks_h")}</h2>
    <p>{t("footer.trademarks")}</p>
    <h2 id="credits">{t("legal.credits_h")}</h2>
    <p>{t("footer.credits")}</p>
    <h2 id="imprint">{t("legal.imprint_h")}</h2>
    <p>{t("footer.imprint")}</p>
    <p class="byline"><time datetime="{updated}">{t("last_updated", date=date_text(updated))}</time></p>
  </article>
</main>

{small_footer(pid)}"""
    head_html = head(pid, title, desc, "website", None, ld_json(graph), owner=True)
    emit(pid, L, page(head_html, main, "Trademark notices, badge credits and the imprint of owen282000.com."))
    return "legal"


IOS_PRIVACY_STYLE = """<style>
  :root { --bg: #F6F8F7; --card: #FFFFFF; --text: #14181C; --muted: #4B5860; --link: #166534; --line: #DDE3E0; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #14181C; --card: #1B2126; --text: #E6EDF0; --muted: #9AA7B0; --link: #30B77E; --line: #2A3238; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 16px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; padding: 32px 16px 48px; }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 1.6rem; line-height: 1.25; margin: 0 0 4px; }
  h2 { font-size: 1.1rem; margin: 0 0 6px; }
  p { margin: 0 0 12px; }
  p:last-child { margin-bottom: 0; }
  section { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px; margin: 14px 0; }
  .muted { color: var(--muted); }
  .lead { font-size: 1.05rem; margin: 18px 0; }
  a { color: var(--link); }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .92em; }
  footer { margin-top: 24px; font-size: .9rem; }
  .lang-row { margin-top: 12px; }
  .lang-row a { margin-right: 10px; }
  .lang-row a[aria-current] { color: var(--text); font-weight: 700; text-decoration: none; }
</style>"""


def build_ios_privacy():
    """The iPhone app's privacy policy, at the fixed address App Store Connect and the app link
    to. It stands alone: its own small style block, no stylesheet, no images, no requests."""
    pid = "ios-privacy"
    raw = page_source(pid)
    PAGE_DATES[(pid, L)] = opt_meta(raw, "updated") or UPDATED
    hreflang = "".join(f'\n<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in alternates(pid))
    doc = f"""<!DOCTYPE html>
<!-- The privacy policy of Life Dashboard Companion for iPhone. Generated by tools/site/build.py: edit the source there, not this file. -->
<html lang="{LANGS[L]["hreflang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta name="color-scheme" content="light dark">
<meta name="description" content="{html.escape(meta(raw, "description"))}">
<title>{html.escape(meta(raw, "title"))}</title>
<link rel="canonical" href="{url_of(pid)}">{hreflang}
<meta name="robots" content="max-image-preview:large">
{IOS_PRIVACY_STYLE}
<link rel="icon" href="/favicon.ico" sizes="48x48">
</head>
<body>
<main>
{body_of(raw).strip()}
{lang_row(pid)}
</main>
</body>
</html>
"""
    emit(pid, L, doc)
    return "ios-privacy"


def build_404():
    """Served for any missing path (deploy/Caddyfile). English only."""
    raw = (I18N / "en" / "pages" / "not-found.html").read_text()
    groups = [("Life Dashboard", [(LD, "Life Dashboard")] + [(f"{LD}{s}/", PARTS[s]["name"]) for s in PRODUCTS]),
              (t("index.h1"), [(f"{LD}guides/", t("footer.all_guides", n=len(GUIDES)))] + [(f"{LD}{g[0]}/", g[1]) for g in GUIDES]),
              ("Owen Vogelaar", [("/", "The developer page"), ("/privacy/", "Privacy"), ("/legal/", t("footer.legal"))])]
    cols = "\n".join(
        f'      <div class="page-group"><h2>{html.escape(name)}</h2>\n      <ul class="page-list">\n'
        + "\n".join(f'        <li><a href="{u}">{html.escape(n)}</a></li>' for u, n in pages) + "\n      </ul></div>"
        for name, pages in groups)
    body = fill(body_of(raw), "pages", f'<div class="page-groups">\n{cols}\n    </div>')
    doc = f"""<!DOCTYPE html>
<!-- Served for any missing path on owen282000.com (see deploy/Caddyfile). Generated by tools/site/build.py. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<meta name="color-scheme" content="light dark">
<title>{meta(raw, "title")}</title>
<link rel="icon" type="image/png" sizes="32x32" href="{LD}img/icon-32.png">
<link rel="stylesheet" href="{LD}site.css">
</head>
<body>
<a class="skip" href="#main">{t("skip")}</a>
{nav(LD)}
{body.strip()}
{footer(LD)}
</body>
</html>
"""
    (SITE / "404.html").write_text(localize(placed(doc, "site-404", "site-404"), "hub", "en"))


FEEDBACK_BOARD = "https://lifedashboard.userjot.com/"


def build_feedback():
    # The address the apps, READMEs and stores link to, so the board can move without touching them.
    out = OUT / "feedback"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={FEEDBACK_BOARD}">
<title>Life Dashboard feedback board</title>
</head>
<body>
<p>Going to the <a href="{FEEDBACK_BOARD}">Life Dashboard feedback board</a>.</p>
</body>
</html>
""")


def build_llms():
    """llms.txt stays one English file at the root and under /life-dashboard/: assistants ask for
    it there, and the proposal has no per-language variant. It names the translations."""
    text = tokens((HERE / "llms.txt.in").read_text())
    for p in (SITE / "llms.txt", OUT / "llms.txt"):
        p.write_text(text)


def build_sitemap():
    """Every page in every language, each with its lastmod and the same xhtml:link alternates as
    its <head>. <lastmod> follows <loc> directly: indexnow.py reads the pair."""
    order = ["hub", "privacy", "legal", "landing"] + PRODUCTS + ["guides"] + GUIDE_IDS + ["ios-privacy"]
    rows = []
    for lang in LANGS:
        for pid in order:
            if (pid, lang) not in BUILT:
                continue
            links = "".join(f'<xhtml:link rel="alternate" hreflang="{h}" href="{u}"/>' for h, u in alternates(pid))
            rows.append(f"  <url><loc>{url_of(pid, lang)}</loc><lastmod>{PAGE_DATES[(pid, lang)]}</lastmod>{links}</url>")
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n")


# ---------------------------------------------------------------------------------------------
# Checks

def structure(pid, lang):
    """What a translation must leave exactly as the English page has it: code, screenshots,
    tables and the fields of a product page that are not prose."""
    src = source(pid, lang).read_text()
    if pid in PRODUCTS:
        d = json.loads(src)
        return {"hero_image": d.get("hero_image"), "updated": d.get("updated"), "guides": d.get("guides"),
                "sections": [(x.get("image"), x.get("image2"), (x.get("code") or {}).get("code"), len(x["bullets"]),
                              (x.get("link") or {}).get("href")) for x in d["sections"]],
                "highlights": len(d["highlights"]), "faq": [(f.get("id"), f.get("open")) for f in d["faq"]],
                "commands": (d.get("commands") or {}).get("code"),
                "compare": [len(r) for r in d["compare"]["rows"]] if d.get("compare") else None}
    body = body_of(src)
    return {"code blocks": re.findall(r"<pre><code>(.*?)</code></pre>", body, re.S) if pid != "landing" else len(re.findall(r"<pre", body)),
            "screenshots": re.findall(IMG_MARK, body) + re.findall(r'<img[^>]* src="([^"]+)"', body),
            "tables": [len(re.findall(r"<tr>", x)) for x in re.findall(r"<table>.*?</table>", body, re.S)],
            "markers": re.findall(r"<!-- BUILD:([\w-]+) -->", body),
            "ids": sorted(re.findall(r'\bid="([^"]+)"', body)),
            "inline code": len(re.findall(r"<code>", body)),
            "links to pages of this site": sorted(h for h in re.findall(r'href="([^"]+)"', body) if not h.startswith(("#", "http", "mailto:")))}


def check(strict=()):
    """Refuse a site that says a live store is still coming, contains a dash we never use, or
    whose languages don't fit together: hreflang that isn't mutual, a translated page that
    links to an English page although its translation exists, a fragment that leads nowhere,
    a title or description used twice. For the languages in `strict` (those marked complete in
    lang.json, or named with --strict) also: a page or string that is still missing, and a
    translation whose code, screenshots or tables differ from the English page."""
    live = {it["id"] for s in ORDER for it in PARTS_BASE[s]["get"] if it["status"] == "live"}
    files = [f for f in SITE.rglob("*.html")] + [SITE / "llms.txt"]
    problems, notes = [], []
    rel = lambda f: str(f.relative_to(ROOT))
    # The App Store campaign of every page in every language, also of a page not translated yet.
    problems += [f"{lang}:{pid}: the App Store campaign {app_place(pid, lang)} is longer than {CT_MAX} characters"
                 for lang in LANGS for pid in PAGES if len(app_place(pid, lang)) > CT_MAX]
    for f in files:
        text = f.read_text()
        for store, phrases in STALE.items():
            if store in live:
                problems += [f"{rel(f)}: says '{ph}' but {store} is live" for ph in phrases if ph in text]
        for token in (PLACE, CT, "{{play_url}}", "{{app_store_url}}", "{{status:"):
            if token in text:
                problems.append(f"{rel(f)}: still says {token}")
        # Every link to our App Store listing carries its campaign, short enough for Apple (the
        # JSON-LD names the plain listing, outside an href).
        for link in re.findall(r'href="(https://apps\.apple\.com/[^"]*/id6824075761[^"]*)"', text):
            ct = re.search(r"[?&;]ct=([^&]*)", link)
            if not ct:
                problems.append(f"{rel(f)}: an App Store link without a campaign (ct): {link}")
            elif len(ct.group(1)) > CT_MAX:
                problems.append(f"{rel(f)}: the App Store campaign {ct.group(1)} is longer than {CT_MAX} characters")
        if "—" in text or "–" in text:
            problems.append(f"{rel(f)}: contains an em or en dash")
        # Every page with the navigation bar gets a skip link past it.
        if '<header class="nav"' in text and ('class="skip" href="#main"' not in text or 'id="main"' not in text):
            problems.append(f"{rel(f)}: needs the skip link and id=\"main\"")
    # Every badge is shown, linked or as "Coming soon", so every file must be there.
    problems += [f"img/badges/{b[0]} is missing" for b in BADGE_FILES.values() if not (OUT / "img" / "badges" / b[0]).exists()]
    # The IndexNow key (indexnow.py): one file in site/ that holds its own name, served at the root.
    if len([f for f in SITE.glob("*.txt") if f.read_text().strip() == f.stem]) != 1:
        problems.append("site/ needs exactly one IndexNow key file, <key>.txt holding <key>")
    llms = (SITE / "llms.txt").read_text()
    problems += [f"llms.txt: the page {g} is missing" for g in GUIDE_IDS + PRODUCTS if f"{BASE}{g}/" not in llms]

    # --- languages
    docs = {key: f.read_text() for key, f in BUILT.items()}
    by_path = {"/" + path_of(pid, lang): (pid, lang) for pid, lang in BUILT}
    seen_title, seen_desc = {}, {}
    for (pid, lang), doc in docs.items():
        name = f"{lang}:{pid}"
        own = url_of(pid, lang)
        if f'<html lang="{LANGS[lang]["hreflang"]}">' not in doc:
            problems.append(f"{name}: <html lang> is not {LANGS[lang]['hreflang']}")
        if f'<link rel="canonical" href="{own}">' not in doc:
            problems.append(f"{name}: the canonical is not the page itself")
        # hreflang: itself, x-default, and every page it names names it back
        alts = re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', doc)
        if alts != alternates(pid):
            problems.append(f"{name}: hreflang links are {alts}, expected {alternates(pid)}")
        if alts and ((LANGS[lang]["hreflang"], own) not in alts or not any(h == "x-default" for h, _ in alts)):
            problems.append(f"{name}: hreflang needs the page itself and x-default")
        for h, u in alts:
            target = by_path.get("/" + u[len(DOMAIN):])
            if not target:
                problems.append(f"{name}: hreflang {h} points at {u}, which is not built")
            elif f'href="{own}">' not in "".join(re.findall(r'<link rel="alternate"[^>]+>', docs[target])):
                problems.append(f"{name}: hreflang is not mutual, {u} does not link back")
        # titles and descriptions: one of each on the whole site
        title = re.search(r"<title>(.*?)</title>", doc, re.S).group(1)
        desc = re.search(r'<meta name="description" content="(.*?)">', doc, re.S).group(1)
        for seen, val, what in ((seen_title, title, "title"), (seen_desc, desc, "description")):
            if val in seen:
                problems.append(f"{name}: the same {what} as {seen[val]}")
            seen[val] = name
        if lang != "en" and (len(html.unescape(title)) > 65 or len(html.unescape(desc)) > 165):
            notes.append(f"{name}: title {len(html.unescape(title))}, description {len(html.unescape(desc))} characters (aim for 60 and 160)")
        # a heading or title never ends with a full stop, in any language
        for tag, inner in [("title", title)] + re.findall(r"<(h[1-6])\b[^>]*>(.*?)</\1>", doc, re.S):
            words = strip_tags(inner)
            if words.endswith((".", "。")) and not words.endswith("..."):
                problems.append(f"{name}: the <{tag}> '{words}' ends with a full stop")
        # links in the page itself (not the <head>, not the JSON-LD)
        body = doc[doc.index("</head>"):]
        ids = set(re.findall(r'\bid="([^"]+)"', body))
        for tag, href in re.findall(r'(<a\b[^>]*\bhref="([^"]*)"[^>]*>)', body):
            if ' lang="' in tag:   # the language menu: the same page in another language
                continue
            if href.startswith(DOMAIN):
                href = "/" + href[len(DOMAIN):]
            if href.startswith("#"):
                if href[1:] and href[1:] not in ids:
                    problems.append(f"{name}: links to {href}, which is not on the page")
                continue
            if not href.startswith("/"):
                continue
            path, _, frag = href.partition("#")
            path = path.split("?")[0]
            if lang != "en" and path in EN_PATH_TO_ID and exists(EN_PATH_TO_ID[path], lang):
                problems.append(f"{name}: links to the English {path} although /{path_of(EN_PATH_TO_ID[path], lang)} exists")
            if frag and path in by_path and f'id="{frag}"' not in docs[by_path[path]]:
                problems.append(f"{name}: links to {href}, but that page has no #{frag}")
    slugs = [path_of(pid, lang) for pid, lang in BUILT]
    problems += [f"two pages share the address /{p}" for p in set(slugs) if slugs.count(p) > 1]

    # --- completeness, for a language that is marked complete or named with --strict
    for lang in LANGS:
        if lang == "en":
            continue
        todo = [pid for pid in PAGES if not exists(pid, lang)]
        own = []
        for pid in PAGES:
            if not exists(pid, lang) or pid in STRING_PAGES:
                continue
            src = source(pid, lang).read_text()
            en = source(pid, "en").read_text()
            if opt_meta(src, "structure") != "own" and structure(pid, lang) != structure(pid, "en"):
                a, b = structure(pid, lang), structure(pid, "en")
                own.append(f"{lang}:{pid}: differs from the English page in {', '.join(k for k in a if a[k] != b[k])}")
            if pid not in PRODUCTS and (opt_meta(src, "title") == opt_meta(en, "title") or opt_meta(src, "description") == opt_meta(en, "description")):
                own.append(f"{lang}:{pid}: the title or description is still the English one")
        missing = sorted(MISSING[lang]) if lang in STRINGS else ["strings.json"]
        if lang in strict:
            problems += [f"{lang}: the page {pid} is not translated ({source(pid, lang).relative_to(ROOT) if source(pid, lang) else STRING_PAGES[pid] + ' in strings.json'})" for pid in todo]
            problems += [f"{lang}: strings.json lacks {k}" for k in missing]
            problems += own
        else:
            notes.append(f"{lang}: still to translate: {len(todo)} of {len(PAGES)} pages, {len(missing)} strings"
                         + (f", {len(own)} pages that differ from the English structure" if own else "")
                         + f" (python3 tools/site/build.py --strict {lang} lists them)")
    for n in notes:
        print("note:", n)
    if problems:
        sys.exit("build check failed:\n  " + "\n  ".join(problems))


def build_language(lang):
    activate(lang)
    out = []
    for s in PRODUCTS:
        if exists(s, lang):
            out.append(build_product(s))
    for g in GUIDE_IDS:
        if exists(g, lang):
            out.append(build_guide(g))
    if exists("guides", lang):
        out.append(build_index())
    for pid, fn in (("landing", build_landing), ("hub", build_hub), ("privacy", build_privacy), ("legal", build_legal),
                    ("ios-privacy", build_ios_privacy)):
        if exists(pid, lang):
            out.append(fn())
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    strict = {c for c, m in LANGS.items() if m.get("complete") and c != "en"}
    if "--strict" in args:
        named = [a for a in args[args.index("--strict") + 1:] if not a.startswith("-")]
        named = [c for a in named for c in a.split(",")]
        unknown = [c for c in named if c not in LANGS]
        if unknown:
            sys.exit(f"--strict: no such language {unknown}; there are {list(LANGS)}")
        strict |= set(named) if named else {c for c in LANGS if c != "en"}
    # A translation's pages are generated in full, so its folder starts empty every time.
    for m in LANGS.values():
        if m["dir"] and (SITE / m["dir"]).exists():
            shutil.rmtree(SITE / m["dir"])
    for lang in LANGS:
        lines = build_language(lang)
        if lang == "en":
            print("\n".join(lines))
        else:
            print(f"{lang}: {len(lines)} pages")
    activate("en")
    build_404()
    build_feedback()
    build_llms()
    build_sitemap()
    check(strict)
    print("ok")
