#!/usr/bin/env python3
"""Build the Life Dashboard site under site/life-dashboard/ (served at owen282000.com/life-dashboard/).

One source for everything that repeats: the navigation, the footer, the install buttons and
cards, the structured data, the store status text, llms.txt and the sitemap. Run it from
anywhere after changing any page or any data below:

    python3 tools/site/build.py

What it writes:
- products/<slug>.json becomes site/life-dashboard/<slug>/index.html (Android, iPhone,
  Home Assistant, Grafana).
- guides/<slug>.html becomes site/life-dashboard/<slug>/index.html. Each guide starts
  with a comment holding its title and description; screenshot placeholders like
  <!-- IMG: pair dialog (A2-pair.png) --> become figures.
- The landing page (site/life-dashboard/index.html) is written by hand. Between its
  <!-- BUILD:name --> and <!-- /BUILD:name --> markers the script fills in the shared parts,
  including the JSON-LD, whose FAQ comes from the questions on the page.
- llms.txt (in site/ and site/life-dashboard/) from llms.txt.in, and site/sitemap.xml.

Store status lives in PARTS only. Text anywhere can say {{status:android}} or {{status:ios}}
and gets the current sentence from STATUS_TEXT.

Launch day for Google Play or the App Store:
1. Download the official badge (Google's Partner Marketing Hub, Apple's Marketing Tools) into
   site/life-dashboard/img/badges/ under the name in BADGES. Never hotlink or embed it,
   never recolor or crop it.
2. In PARTS, set that entry's "status" to "live" (check its "href" and "note").
3. Update STATUS_TEXT, run the script. It refuses to build while a page still says the store is
   coming. Live stores then lead every hero and install card with their official badge.
"""
import html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SITE = ROOT / "site"
OUT = SITE / "life-dashboard"
DOMAIN = "https://owen282000.com/"
BASE = DOMAIN + "life-dashboard/"
UPDATED = "2026-10-06"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def date_text(iso):
    """2026-10-12 as October 12, 2026, for the byline."""
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{MONTHS[m - 1]} {d}, {y}"


# The date each page last changed, so a lastmod in the sitemap means something: a page without
# an `updated:` line (guides) or "updated" field (products) keeps UPDATED, the site's launch day.
PAGE_DATES = {}

REPO = "https://github.com/owen282000/life-dashboard-companion-app"
REPO_IOS = "https://github.com/owen282000/life-dashboard-companion-app-ios"
REPO_HA = "https://github.com/owen282000/life-dashboard-ha"
REPO_STACK = "https://github.com/owen282000/life-dashboard-stack"
APK = f"{REPO}/releases/latest/download/app-release.apk"
HACS = "https://my.home-assistant.io/redirect/hacs_repository/?owner=owen282000&amp;repository=life-dashboard-ha&amp;category=integration"

# ---------------------------------------------------------------------------------------------
# The four parts and where to get them. "kind": "store" is the store the site leads with once it
# is live. Until then, the entry marked "primary" leads, and pending stores show as "Coming".
PARTS = {
    "android": {
        "name": "Android app", "full": "Life Dashboard Companion for Android",
        "line": "Health Connect and screen time per app",
        "glyph": '<rect x="6" y="2.5" width="12" height="19" rx="2.5"/><path d="M10.5 18.5h3"/>',
        "get_title": "Get the Android app", "req_short": "Android 8.0 or newer; health data from Android 9.",
        "get": [
            {"id": "play", "kind": "store", "name": "Google Play", "status": "soon", "soon_text": "Google Play: coming, as a paid listing of the same app",
             "href": "https://play.google.com/store/apps/details?id=com.owen282000.lifedashboard",
             "note": "In closed testing now. It will be a paid listing; the APK on GitHub stays free."},
            {"id": "apk", "name": "Free APK on GitHub", "status": "live", "href": APK, "primary": True, "cta": "Download the free APK",
             "note": "Open it on your phone and allow installs from your browser once. Each new release is on GitHub, or Obtainium updates it for you."},
            {"id": "obtainium", "name": "Obtainium", "status": "live",
             "href": "https://apps.obtainium.imranr.dev/redirect?r=obtainium://add/" + REPO,
             "note": "An app updater for GitHub apps: installs the same APK and keeps it up to date. Open this link on your phone."},
            {"id": "fdroid", "name": "F-Droid", "status": "soon", "href": "https://f-droid.org/packages/com.owen282000.lifedashboard/",
             "note": "Submitted and in review."},
        ],
        "requires": "Android 9 or newer with Health Connect for health data; Android 8.0 or newer for screen time.",
    },
    "ios": {
        "name": "iPhone app", "full": "Life Dashboard Companion for iPhone",
        "line": "Apple Health, with the same payload",
        "glyph": '<rect x="6" y="2.5" width="12" height="19" rx="3"/><path d="M10 5h4"/>',
        "get_title": "Get the iPhone app", "req_short": "iOS 17 or newer. Building it takes a Mac and about an hour.",
        "get": [
            {"id": "appstore", "kind": "store", "name": "App Store", "status": "soon", "href": "", "pill": "TestFlight beta next", "pill_icon": "testflight",
             "note": "Planned after the TestFlight beta."},
            {"id": "xcode", "name": "Build with Xcode", "status": "live", "href": REPO_IOS + "#build-and-install", "primary": True, "cta": "Build with Xcode",
             "note": "From source, on a Mac with Xcode: about an hour the first time. Your settings stay when you run a newer version."},
            {"id": "testflight", "name": "TestFlight", "status": "soon", "href": "",
             "note": "A public beta is next. No Mac needed then."},
        ],
        "requires": "iOS 17 or newer. Building it needs a Mac with Xcode; with a free Apple Account you run it from Xcode again every 7 days.",
    },
    "home-assistant": {
        "name": "Home Assistant integration", "nav": "Home Assistant", "full": "Life Dashboard integration for Home Assistant",
        "line": "Sensors, statistics and a year of history",
        "glyph": '<path d="M3.5 11 12 3.5l8.5 7.5"/><path d="M5.5 9.5V20h13V9.5"/><circle cx="12" cy="13.5" r="2"/><path d="M12 15.5V20"/>',
        "get_title": "Install the integration", "req_short": "Home Assistant 2026.3 or newer.",
        "get": [
            {"id": "hacs", "kind": "store", "name": "HACS", "status": "live", "href": HACS, "cta": "Open in HACS",
             "note": "As a custom repository for now; the default HACS list is pending. Restart Home Assistant after the download."},
            {"id": "ha-setup", "name": "Setup steps", "status": "live", "href": "health-connect-home-assistant/#set-it-up", "rel": True,
             "note": "Add the integration, check the address the phone should use, scan the QR code."},
            {"id": "ha-source", "name": "Source on GitHub", "status": "live", "href": REPO_HA,
             "note": "Release notes and the manual install."},
        ],
        "requires": "Home Assistant 2026.3 or newer, with HACS.",
    },
    "grafana": {
        "name": "Grafana stack", "full": "Life Dashboard stack",
        "line": "Postgres and Grafana dashboards, self-hosted",
        "glyph": '<path d="M4 20h16"/><path d="M6.5 16v-4"/><path d="M11 16V7"/><path d="M15.5 16v-6"/><path d="M20 16V4"/>',
        "get_title": "Run the stack", "req_short": "Docker with Compose.",
        "get": [
            {"id": "compose", "kind": "store", "name": "Docker Compose", "status": "live", "href": REPO_STACK + "#quick-start", "cta": "Run with Docker Compose",
             "note": "Clone the repository, set four values in .env, then docker compose up -d --build."},
            {"id": "demo", "name": "Demo data", "status": "live", "href": REPO_STACK + "#try-it-without-a-phone",
             "note": "60 days of made-up data for two phones, before any phone of yours is involved."},
        ],
        "requires": "Docker with Compose on a machine your phone can reach.",
    },
}
ORDER = ["android", "ios", "home-assistant", "grafana"]

# One sentence per app about where to get it, used through {{status:android}} and {{status:ios}}.
STATUS_TEXT = {
    "android": "Today you install the signed APK from GitHub, or through Obtainium, which keeps it up to date. Google Play is in closed testing, and F-Droid is reviewing the app.",
    "ios": "Today you build it from source with Xcode on a Mac. A public TestFlight beta is next.",
}
# Phrases that must be gone once a store is live (checked on every build).
STALE = {"play": ["coming to Google Play", "Google Play is in closed testing", "will be a paid listing"],
         "appstore": ["App Store release is planned", "no App Store", "Planned after the TestFlight beta"],
         "testflight": ["TestFlight beta is next", "TestFlight beta next", "A public beta is next"],
         "fdroid": ["F-Droid is reviewing"],
         "play_paid": []}

# Official badge artwork, stored in img/badges/ (the site loads nothing from anyone else).
BADGES = {"play": ("google-play.svg", "Get it on Google Play"),
          "appstore": ("app-store.svg", "Download on the App Store")}

GUIDES = [
    ("health-connect-home-assistant", "Samsung Health and Health Connect in Home Assistant", "Home Assistant",
     "Samsung Health, Garmin, Fitbit, Oura and Withings data as sensors, with a year of history."),
    ("health-connect-webhook", "Health Connect to a webhook", "Webhooks",
     "The JSON payload, signatures, retries and receivers for n8n and Node-RED."),
    ("screen-time-home-assistant", "Screen time in Home Assistant", "Screen time",
     "Minutes per app as sensors, limits you set yourself, and several phones."),
    ("smart-scale-to-samsung-health", "Smart scale to Samsung Health", "Smart scale",
     "Weight, body fat and blood pressure from Home Assistant into Health Connect."),
    ("health-data-api", "A web API for Health Connect or Apple Health", "API",
     "Why neither has one, and how to get the data onto your server anyway."),
    ("samsung-health-export", "Samsung Health to your own server", "Export",
     "Galaxy Watch data as JSON in your own database, n8n flow or script."),
    ("fitbit-home-assistant", "Fitbit and Pixel Watch in Home Assistant", "Fitbit",
     "Through Health Connect, with no Fitbit Web API and no Google Cloud project."),
    ("garmin-home-assistant", "Garmin in Home Assistant", "Garmin",
     "Steps, sleep and heart rate from Garmin Connect, with no Garmin login in Home Assistant."),
    ("health-data-own-ai", "Ask your own AI about your health data", "Your own AI",
     "A local model reads your history through a read-only MCP server. No cloud."),
]
GUIDES = [g for g in GUIDES if (Path(__file__).resolve().parent / "guides" / f"{g[0]}.html").exists()]
GUIDE_NAMES = {g[0]: g[1] for g in GUIDES}
GUIDE_ABOUT = {
    "health-data-api": ["#android", "#ios"],
    "samsung-health-export": ["#android"],
    "fitbit-home-assistant": ["#android", "#integration"],
    "garmin-home-assistant": ["#android", "#integration"],
    "health-data-own-ai": ["#integration", "#stack"],
    "health-connect-home-assistant": ["#android", "#integration"],
    "health-connect-webhook": ["#android", "#ios"],
    "screen-time-home-assistant": ["#android", "#integration"],
    "smart-scale-to-samsung-health": ["#integration", "#android"],
}

IMAGES = {
    "A1-health": ("phone", 720, 1476, "The Health tab of the Android app"),
    "A2-pair": ("phone", 720, 1540, "The Pair with a receiver dialog in the Android app"),
    "A4-screen-time": ("phone", 720, 1540, "The Screen Time tab of the Android app"),
    "A5-receive": ("phone", 720, 1540, "The Receive settings in the Android app"),
    "A6-webhook": ("phone", 720, 1540, "The Webhook settings with an HMAC signing secret"),
    "A7-logs": ("phone", 720, 1540, "The delivery log in the Android app"),
    "H1-dashboard": ("phone", 720, 1598, "The example dashboard in Home Assistant on a phone"),
    "H2-qr": ("card", 800, 668, "The Life Dashboard integration in Home Assistant showing a pairing QR code"),
    "H3-history": ("phone", 720, 1598, "History graphs in Home Assistant on a phone"),
    "H4-apps": ("phone", 720, 1598, "Screen time per app in Home Assistant on a phone"),
    "H5-today": ("phone", 720, 1052, "Today's steps, distance, calories, heart rate and last sleep in Home Assistant, with steps per week"),
    "ios-health": ("phone", 720, 1464, "The Health tab of the iPhone app with Apple Health types"),
    "ios-schedule": ("phone", 720, 1378, "The sync schedule of the iPhone app at fixed times with quiet hours"),
    "ios-logs": ("phone", 720, 1464, "The sync history of the iPhone app"),
    "ios-mqtt": ("phone", 720, 1378, "Webhook and MQTT settings in the iPhone app"),
    "g-overview": ("wide", 1400, 728, "The overview dashboard of the Grafana stack with demo data"),
    "g-activity": ("wide", 1400, 1260, "The activity dashboard of the Grafana stack"),
    "g-sleep": ("wide", 1400, 895, "The sleep dashboard of the Grafana stack"),
    "g-heart-body": ("wide", 1400, 1363, "The heart and body dashboard of the Grafana stack"),
    "g-screen-time": ("wide", 1400, 1196, "The screen time dashboard of the Grafana stack"),
    "g-data": ("wide", 1400, 1260, "The data and sync dashboard of the Grafana stack"),
}

# Phone screenshots cut short of the full screen; they fade out at the bottom.
CUT = {"H5-today"}

NEXT = {
    "health-data-api": ("Install the app on the phone and point it at your URL. The payload reference has every field and a receiver in Python and Node.js.",
        [("btn-primary btn-store", "../android/#get", "Get the Android app"), ("btn-ghost", "../ios/#get", "Get the iPhone app")]),
    "samsung-health-export": ("Switch on Health Connect in Samsung Health, install the app, and tap <strong>Test ping</strong> against your URL.",
        [("btn-primary btn-store", "../android/#get", "Get the Android app"), ("btn-ghost", f"{REPO}/blob/main/docs/webhook.md", "Payload reference")]),
    "fitbit-home-assistant": ("Two installs: the integration from HACS and the app on your phone. After that, pairing takes a minute.",
        [("btn-primary btn-store", HACS, "Open in HACS"), ("btn-ghost", "../android/#get", "Get the Android app")]),
    "garmin-home-assistant": ("Two installs: the integration from HACS and the app on your phone. After that, switch on Health Connect in Garmin Connect and pair with one QR code.",
        [("btn-primary btn-store", HACS, "Open in HACS"), ("btn-ghost", "../android/#get", "Get the Android app")]),
    "health-data-own-ai": ("Start with the data: the integration or the stack, and a backfill of up to a year from the app.",
        [("btn-primary btn-store", "../home-assistant/", "The Home Assistant route"), ("btn-ghost", "../grafana/", "The stack route")]),
    "health-connect-home-assistant": ("Two installs: the integration from HACS and the app on your phone. After that, pairing takes a minute.",
        [("btn-primary btn-store", HACS, "Open in HACS"), ("btn-ghost", "../android/#get", "Get the Android app")]),
    "health-connect-webhook": ("Install the app, point it at your URL and tap <strong>Test ping</strong>. The payload reference has every field and a receiver in Python and Node.js.",
        [("btn-primary btn-store", "../android/#get", "Get the Android app"), ("btn-ghost", f"{REPO}/blob/main/docs/webhook.md", "Payload reference")]),
    "screen-time-home-assistant": ("Screen time doesn't need Health Connect. Any phone or tablet with Android 8.0 or newer works.",
        [("btn-primary btn-store", "../android/#get", "Get the Android app"), ("btn-ghost", HACS, "Open the integration in HACS")]),
    "smart-scale-to-samsung-health": ('You need the Life Dashboard integration 0.7.0 or newer and the app on your phone, paired as in the <a href="../health-connect-home-assistant/">Health Connect guide</a>.',
        [("btn-primary btn-store", HACS, "Open in HACS"), ("btn-ghost", "../android/#get", "Get the Android app")]),
}

# Structured data for the project and its four parts, written into the landing page and, for
# each part, into its own product page.
ME = {"@type": "Person", "@id": f"{BASE}#owen", "name": "Owen Vogelaar", "url": DOMAIN,
      "sameAs": ["https://github.com/owen282000"]}
WEBSITE = {"@type": "WebSite", "@id": f"{BASE}#website", "url": BASE, "name": "Life Dashboard", "inLanguage": "en"}
PROJECT = {"@type": "CreativeWorkSeries", "@id": f"{BASE}#project", "name": "Life Dashboard", "url": BASE,
           "description": "Open-source project by Owen Vogelaar: apps for Android and iPhone that send health data to Home Assistant, MQTT or a webhook, a Home Assistant integration and a self-hosted Grafana stack.",
           "author": {"@id": f"{BASE}#owen"},
           "hasPart": [{"@id": f"{BASE}#android"}, {"@id": f"{BASE}#ios"}, {"@id": f"{BASE}#integration"}, {"@id": f"{BASE}#stack"}]}
ENTITY_ID = {"android": "#android", "ios": "#ios", "home-assistant": "#integration", "grafana": "#stack"}
ENTITIES = {
    "android": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#android", "name": "Life Dashboard Companion",
        "alternateName": ["Life Dashboard", "Life Dashboard Companion for Android"],
        "identifier": "com.owen282000.lifedashboard",
        "description": "Life Dashboard Companion is an open-source Android app that sends Health Connect data and screen time per app to Home Assistant, MQTT or your own webhook, with no cloud and no account.",
        "operatingSystem": "Android 8.0 or newer (health data: Android 9 or newer with Health Connect)",
        "applicationCategory": "HealthApplication", "applicationSubCategory": "Home automation",
        "featureList": ["Reads 33 Health Connect data types", "Screen time per app",
                        "Home Assistant integration with QR pairing and up to a year of history",
                        "MQTT Discovery for Home Assistant",
                        "Webhooks with JSON, HMAC-SHA256 signatures and client certificates",
                        "Writes scale and blood pressure readings from Home Assistant into Health Connect"],
        "inLanguage": ["en", "de", "nl"], "url": f"{BASE}android/",
        "downloadUrl": f"{REPO}/releases/latest", "license": "https://opensource.org/licenses/MIT",
        "isPartOf": {"@id": f"{BASE}#project"}, "author": {"@id": f"{BASE}#owen"},
        "sameAs": [REPO], "screenshot": f"{BASE}img/A1-health.webp"},
    "ios": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#ios", "name": "Life Dashboard Companion for iPhone",
        "alternateName": "Life Dashboard Companion for iOS",
        "description": "Life Dashboard Companion for iPhone is an open-source iPhone app that sends Apple Health data to Home Assistant, MQTT or your own webhook, with no cloud and no account.",
        "operatingSystem": "iOS 17 or newer", "applicationCategory": "HealthApplication",
        "inLanguage": ["en", "de", "nl"], "url": f"{BASE}ios/", "license": "https://opensource.org/licenses/MIT",
        "isPartOf": {"@id": f"{BASE}#project"}, "author": {"@id": f"{BASE}#owen"},
        "sameAs": [REPO_IOS], "screenshot": f"{BASE}img/ios-health.webp"},
    "home-assistant": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#integration", "name": "Life Dashboard integration for Home Assistant",
        "description": "The Life Dashboard integration is an open-source Home Assistant custom integration, installed through HACS, that turns data from the Life Dashboard Companion apps into sensors and long-term statistics, paired by QR code.",
        "applicationCategory": "UtilitiesApplication", "applicationSubCategory": "Home Assistant integration",
        "operatingSystem": "Home Assistant 2026.3 or newer", "url": f"{BASE}home-assistant/",
        "license": "https://opensource.org/licenses/MIT", "isPartOf": {"@id": f"{BASE}#project"},
        "author": {"@id": f"{BASE}#owen"}, "sameAs": [REPO_HA]},
    "grafana": {
        "@type": "SoftwareApplication", "@id": f"{BASE}#stack", "name": "Life Dashboard stack",
        "description": "The Life Dashboard stack is an open-source Docker Compose setup with a receiver, Postgres and six Grafana dashboards for data from the Life Dashboard Companion apps.",
        "applicationCategory": "UtilitiesApplication", "applicationSubCategory": "Self-hosted backend",
        "operatingSystem": "Linux, macOS or Windows with Docker", "url": f"{BASE}grafana/",
        "license": "https://opensource.org/licenses/MIT", "isPartOf": {"@id": f"{BASE}#project"},
        "author": {"@id": f"{BASE}#owen"}, "sameAs": [REPO_STACK]},
}
ENTITY_NAME = {ENTITY_ID[k]: e["name"] for k, e in ENTITIES.items()}

# Every part is free to download today (the APK, the source, HACS, Compose). The paid Google
# Play listing gets an Offer of its own once it is live.
FREE = {"@type": "Offer", "price": "0", "priceCurrency": "EUR"}
for _e in ENTITIES.values():
    _e["offers"] = FREE
SOURCE_CODE = {"@type": "SoftwareSourceCode", "codeRepository": REPO, "programmingLanguage": "Kotlin",
               "license": "https://opensource.org/licenses/MIT", "targetProduct": {"@id": f"{BASE}#android"}}

GH = '<svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'

# Plain glyphs for the buttons. Not the stores' logos: a live store gets its official badge.
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
    "compose": '<rect x="3.5" y="9" width="17" height="10" rx="2"/><path d="M7 9V6h4v3M13 9V6h4v3"/>',
    "demo": '<path d="M4 19V5m0 14h16M8 15v-3m4 3V9m4 6v-5m4 5V7"/>',
}


def svg(path, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f'<svg{c} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>'


def store_button(item, fallback, prefix=""):
    """Live Google Play or App Store: the official badge. Live HACS or Compose: a store-style
    button. Pending: a dashed text button that leads to the install section."""
    live = item["status"] == "live"
    if live and item["id"] in BADGES:
        f, alt = BADGES[item["id"]]
        return f'<a class="store-badge" href="{item["href"]}"><img src="{prefix}img/badges/{f}" alt="{alt}" height="48"></a>'
    if live:
        return lead_button(dict(item, kind=""), prefix)
    top = "Coming soon to the" if item["id"] == "appstore" else "Coming soon to"
    return (f'<a class="store-btn soon" href="{fallback}">{svg(ICONS[item["id"]])}'
            f'<span><small>{top}</small><b>{item["name"]}</b></span></a>')


def store_of(slug):
    return next((it for it in PARTS[slug]["get"] if it.get("kind") == "store"), None)


def lead_item(slug):
    """What a hero or card leads with: the store once it's live, otherwise the primary route."""
    store = store_of(slug)
    if store and store["status"] == "live":
        return store
    return next(it for it in PARTS[slug]["get"] if it.get("primary"))


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
            out.append(f'<span class="soon-tag">{it.get("soon_text", it["name"] + ": coming").replace("F-Droid", "F&#8209;Droid")}</span>')
    return sep.join(out)


def get_card_compact(slug, prefix):
    """The landing page's install card: the lead button and one line with the other routes.
    The full card, with a note per route, is on the product page."""
    p = PARTS[slug]
    lead = lead_item(slug)
    rest = [it for it in p["get"] if it is not lead]
    return f"""<article class="get-card compact" id="get-{slug}">
        <header><span class="part-ico">{svg(p["glyph"])}</span><div><h3><a href="{prefix}{slug}/">{p["full"]}</a></h3><p>{p["req_short"]}</p></div></header>
        {lead_button(lead, prefix)}
        <p class="get-alt">{alt_links(rest, prefix)}</p>
      </article>"""


def get_card(slug, prefix, req=True):
    p = PARTS[slug]
    page = f"{prefix}{slug}/"
    lead = lead_item(slug)
    rows = []
    for it in p["get"]:
        if it is lead:
            continue
        live = it["status"] == "live"
        tag = '<span class="status live">Available</span>' if live else '<span class="status soon">Coming</span>'
        name = f'<a href="{href_of(it, prefix)}">{it["name"]}</a>' if live else it["name"]
        rows.append(f'<li>{svg(ICONS[it["id"]], "li-ico")}<span><b>{name}</b> {tag}<small>{it["note"]}</small></span></li>')
    note = f'<p class="store-note">{lead["note"]}</p>' if lead.get("note") else ""
    reqs = f'<p class="get-req">{p["requires"]}</p>' if req else ""
    title = f'<a href="{page}">{p["full"]}</a>'
    return f"""<article class="get-card" id="get-{slug}">
        <header><span class="part-ico">{svg(p["glyph"])}</span><div><h3>{title}</h3><p>{p["line"]}</p></div></header>
        {lead_button(lead, prefix)}
        {note}
        <ul class="get-list">
          {"".join(rows)}
        </ul>
        {reqs}
      </article>"""


def get_section(prefix):
    cards = "\n      ".join(get_card_compact(s, prefix) for s in ORDER)
    return f"""<div class="section-head">
      <div class="kicker">Get it</div>
      <h2>Pick your phone, then pick where the data goes</h2>
      <p>Using Home Assistant? Add the integration first; the app scans its QR code.</p>
    </div>
    <div class="get-grid">
      {cards}
    </div>"""


def android_coming():
    """The Android line in the hero: what is still coming, from PARTS."""
    soon = {it["id"]: it for it in PARTS["android"]["get"] if it["status"] == "soon"}
    names = (["Google Play (paid)"] if "play" in soon else []) + (["F&#8209;Droid"] if "fdroid" in soon else [])
    if not names:
        return ""
    return (" and ".join(names) + (" are" if len(names) > 1 else " is") + " coming.")


def hero_stores(prefix):
    """Landing hero and final call to action: live stores lead with their official badges.
    While Google Play is pending, a working "Install today" button leads, a demo needs no phone,
    and one line per phone says how to get it today and what is coming. Once Google Play is live,
    small pills say what is still coming."""
    stores = {s: store_of(s) for s in ("android", "ios")}
    live = [s for s in ("ios", "android") if stores[s]["status"] == "live"]  # Apple: App Store badge first
    btns = [store_button(stores[s], "", prefix) for s in live]
    if len(live) < 2:
        btns.insert(0, f'<a class="btn btn-primary btn-store" href="{prefix}#get">Install today</a>')
        btns.insert(1, f'<a class="btn btn-ghost btn-store" href="{prefix}grafana/#dashboards">See the demo dashboards</a>')
    out = '<div class="cta-row stores">\n        ' + "\n        ".join(btns) + "\n      </div>"
    if stores["android"]["status"] != "live":
        out += ('\n      <ul class="install-paths">'
                f'<li>{svg(PARTS["android"]["glyph"])}<span><b>Android</b> Free APK today. {android_coming()}</span></li>'
                f'<li>{svg(PARTS["ios"]["glyph"])}<span><b>iPhone</b> <a href="{prefix}ios/#building">Build it with Xcode</a> on a Mac, about an hour. TestFlight beta next.</span></li>'
                '</ul>')
        return out
    pills = [f'<a class="soon-pill" href="{"#get-" + s if not prefix else prefix + s + "/#get"}">'
             f'{svg(ICONS[stores[s].get("pill_icon", stores[s]["id"])])}{stores[s].get("pill", "Coming soon to " + stores[s]["name"])}</a>'
             for s in ("android", "ios") if s not in live]
    if pills:
        out += '\n      <div class="soon-row">\n        ' + "\n        ".join(pills) + "\n      </div>"
    return out


def status_line():
    return "Coming to Google Play and F-Droid. On iPhone, a TestFlight beta is next."


def nav(prefix, active=None):
    def a(href, label, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{href}"{cur}>{label}</a>'
    on_product = active in PARTS
    repo = {"ios": REPO_IOS, "home-assistant": REPO_HA, "grafana": REPO_STACK}.get(active, REPO)
    links = "\n      ".join([
        a(f"{prefix}android/", "Android", "android"),
        a(f"{prefix}ios/", "iPhone", "ios"),
        a(f"{prefix}home-assistant/", PARTS["home-assistant"]["nav"], "home-assistant"),
        a(f"{prefix}grafana/", "Grafana", "grafana"),
        a(f"{prefix}#guides", "Guides", "guides"),
        a("#faq" if on_product else f"{prefix}#faq", "FAQ", "faq"),
    ])
    home = prefix or "./"
    install = "#get" if on_product else f"{prefix}#get"
    return f"""<header class="nav">
  <div class="wrap">
    <a class="brand" href="{home}" aria-label="Life Dashboard home">
      <img class="mark" src="{prefix}img/icon-180.png" alt="" width="34" height="34">
      Life Dashboard
    </a>
    <nav class="nav-links" aria-label="Main">
      {links}
    </nav>
    <div class="nav-cta">
      <a class="btn btn-ghost btn-sm" href="{repo}">
        {GH}
        GitHub
      </a>
      <a class="btn btn-primary btn-sm" href="{install}">Install</a>
    </div>
  </div>
</header>"""


def parts_strip(prefix):
    """Under the landing hero: the two apps, then the places the data can go."""
    def cell(href, glyph, name, line):
        return (f'<a href="{href}"><span class="part-ico">{svg(glyph)}</span>'
                f'<span><b>{name}</b><small>{line}</small></span></a>')
    short = {"android": "Health Connect, screen time", "ios": "Apple Health"}
    phones = "".join(cell(f"{prefix}{s}/", PARTS[s]["glyph"], PARTS[s]["name"], short[s]) for s in ("android", "ios"))
    webhook_glyph = '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5"/>'
    dests = (cell(f"{prefix}home-assistant/", PARTS["home-assistant"]["glyph"], "Home Assistant", "Sensors and history")
             + cell(f"{prefix}grafana/", PARTS["grafana"]["glyph"], "Grafana stack", "Postgres and dashboards")
             + cell(f"{prefix}#own-server", webhook_glyph, "Your own server", "MQTT or JSON"))
    return f"""<nav class="parts-strip" aria-label="The apps and where the data goes"><div class="wrap">
    <div class="ps-group"><span class="ps-label">On your phone</span><div class="ps-cells two">{phones}</div></div>
    <div class="ps-group"><span class="ps-label">On your server</span><div class="ps-cells three">{dests}</div></div>
  </div></nav>"""


def footer(prefix):
    home = prefix or "./"
    prods = "\n          ".join(f'<li><a href="{prefix}{s}/">{PARTS[s]["name"]}</a></li>' for s in ORDER)
    guides = "\n          ".join(f'<li><a href="{prefix}{g[0]}/">{g[1]}</a></li>' for g in GUIDES)
    return f"""<footer class="footer">
  <div class="wrap">
    <div class="cols">
      <div class="about">
        <a class="brand" href="{home}"><img class="mark" src="{prefix}img/icon-180.png" alt="" width="34" height="34"> Life Dashboard</a>
        <p>Life Dashboard is an open-source project by <a href="https://github.com/owen282000">Owen Vogelaar</a>, in four parts: the Life Dashboard Companion apps for Android and iPhone, a Home Assistant integration and a Grafana stack. It isn't related to other apps or templates called Life Dashboard. Questions go to <a href="{REPO}/discussions">Discussions</a>.</p>
        <p>This site sets no cookies, runs no analytics and loads nothing from anyone else. <a href="/privacy/">Site privacy</a>.</p>
        <p class="imprint">Owen Vogelaar, trading as oVog Enterprise · KvK 81085583 · <a href="mailto:owen282000@hotmail.com">owen282000@hotmail.com</a></p>
      </div>
      <div>
        <h2 class="foot-h">Products</h2>
        <ul>
          {prods}
        </ul>
      </div>
      <div>
        <h2 class="foot-h">Guides</h2>
        <ul>
          {guides}
        </ul>
      </div>
      <div>
        <h2 class="foot-h">Docs and source</h2>
        <ul>
          <li><a href="{REPO}/blob/main/docs/usage.md">Android setup guide</a></li>
          <li><a href="{REPO_IOS}/blob/main/docs/usage.md">iPhone setup guide</a></li>
          <li><a href="{REPO_HA}/blob/main/docs/entities.md">Integration: sensors and statistics</a></li>
          <li><a href="{REPO}/blob/main/docs/webhook.md">Payload reference</a></li>
          <li><a href="{REPO}/blob/main/docs/brands/README.md">Brand guides</a></li>
          <li><a href="{REPO}/blob/main/PRIVACY.md">Privacy policy for Android</a></li>
          <li><a href="{prefix}ios/privacy/">Privacy policy for iPhone</a></li>
          <li><a href="{REPO}/blob/main/AI_POLICY.md">AI policy</a></li>
          <li><a href="https://github.com/owen282000?tab=repositories&amp;q=life-dashboard">All four repositories</a></li>
        </ul>
      </div>
    </div>
    <p class="legal">Home Assistant is a trademark of the Open Home Foundation. Health Connect, Google Play, Google Health, Fitbit and Pixel Watch are trademarks of Google LLC. Apple, Apple Health, Apple Watch, iPhone, Xcode and TestFlight are trademarks of Apple Inc. App Store is a service mark of Apple Inc. Grafana is a trademark of Grafana Labs. Samsung Health, Garmin Connect, Oura and Withings belong to their owners. Life Dashboard is an independent project and is not affiliated with or endorsed by any of them. Screenshots show made-up data.</p>
  </div>
</footer>"""


def head(title, desc, url, prefix, og_type="website", og_title=None, ld=None):
    ldtag = f'\n<script type="application/ld+json">\n{ld}\n</script>' if ld else ""
    return f"""<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="max-image-preview:large">
<meta name="theme-color" content="#101418">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}img/icon-32.png">
<link rel="apple-touch-icon" href="{prefix}img/icon-180.png">
<link rel="stylesheet" href="{prefix}site.css">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Life Dashboard">
<meta property="og:title" content="{html.escape(og_title or title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}img/social.png">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="640">
<meta property="og:image:alt" content="Life Dashboard Companion: your health data, your server. No cloud.">
<meta name="twitter:card" content="summary_large_image">{ldtag}
</head>"""


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def tokens(s):
    return s.replace("{{status:android}}", STATUS_TEXT["android"]).replace("{{status:ios}}", STATUS_TEXT["ios"])


def image(name, prefix, cls="", eager=False):
    kind, w, h, alt = IMAGES[name]
    load = ' fetchpriority="high"' if eager else ' loading="lazy"'
    img = f'<img src="{prefix}img/{name}.webp" alt="{alt}" width="{w}" height="{h}"{load}>'
    if kind == "phone":
        cls = f"{cls} cut".strip() if name in CUT else cls
        return f'<div class="phone {cls}" style="aspect-ratio: {w} / {h}">{img}</div>'
    if kind == "card":
        return f'<figure class="qr-card {cls}">{img}</figure>'
    return (f'<div class="wide-shot {cls}"><div class="wide-bar"><i></i><i></i><i></i></div>'
            f'<a class="shot-link" href="{prefix}img/{name}.webp" aria-label="{alt}, full size">{img}</a></div>')


def faq_entity(qa):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]}


def breadcrumb(name, url):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Life Dashboard", "item": BASE},
        {"@type": "ListItem", "position": 2, "name": name, "item": url}]}


def ld_json(graph):
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False)


def page(head_html, body, comment):
    return f"""<!DOCTYPE html>
<!-- {comment} Generated by tools/site/build.py: edit the source there, not this file. -->
<html lang="en">
{head_html}
<body>
<a class="skip" href="#main">Skip to content</a>

{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------------------------
# Guides

def opt_meta(src, key):
    m = re.search(rf"^\s*{key}:\s*(.+)$", src, re.M)
    return m.group(1).strip() if m else None


def meta(src, key):
    m = re.search(rf"^\s*{key}:\s*(.+)$", src, re.M)
    if not m:
        sys.exit(f"missing {key}")
    return m.group(1).strip()


PURPLE = {"A4-screen-time", "H4-apps"}


def figure(m):
    name = m.group(1)
    kind, w, h, alt = IMAGES[name]
    tone = " purple" if name in PURPLE else ""
    if kind == "phone":
        return f'<figure class="shot{tone}"><a class="shot-link" href="../img/{name}.webp" aria-label="{alt}, full size">{image(name, "../")}</a></figure>'
    return (f'<figure class="shot wide"><a class="shot-link" href="../img/{name}.webp" aria-label="{alt}, full size">'
            f'<img src="../img/{name}.webp" alt="{alt}" width="{w}" height="{h}" loading="lazy"></a></figure>')


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", strip_tags(text).lower()).strip("-")


def enhance(body, short):
    """Accessible tables and code blocks, ids on headings, the guide FAQ heading."""
    def table(m):
        cap = re.search(r"<h[23][^>]*>(.*?)</h[23]>(?![\s\S]*<h[23])", body[:m.start()], re.S)
        label = strip_tags(cap.group(1)) if cap else "Table"
        t = m.group(0)
        t = re.sub(r"<th></th>", '<th scope="col">Feature</th>', t)
        t = re.sub(r"<thead>(.*?)</thead>", lambda x: "<thead>" + x.group(1).replace("<th>", '<th scope="col">') + "</thead>", t, flags=re.S)
        t = re.sub(r"(<tbody>.*?</tbody>)", lambda x: re.sub(r"<tr>\s*<td>(.*?)</td>", r'<tr><th scope="row">\1</th>', x.group(1), flags=re.S), t, flags=re.S)
        return f'<div class="table-wrap" tabindex="0" role="region" aria-label="{html.escape(label)}">{t}</div>'
    body = re.sub(r"<table>.*?</table>", table, body, flags=re.S)
    body = body.replace("<pre><code>", '<pre tabindex="0"><code>')
    body = re.sub(r"<h2>(.*?)</h2>", lambda m: f'<h2 id="{slugify(m.group(1))}">{m.group(1)}</h2>', body)
    body = body.replace('<h2 id="faq">FAQ</h2>', '<h2 id="faq">Common questions</h2>')
    return body


def build_guide(slug, short):
    src = tokens((HERE / "guides" / f"{slug}.html").read_text())
    title, desc = meta(src, "title"), meta(src, "description")
    updated = opt_meta(src, "updated") or UPDATED
    PAGE_DATES[f"{slug}/"] = updated
    body = re.sub(r"<!--.*?-->", lambda m: m.group(0) if "IMG" in m.group(0) else "", src, count=1, flags=re.S)
    body = re.sub(r"<!--\s*IMG:[^>]*?\(?([A-Za-z]\d?-[a-z-]+)(?:\.png|\.webp)?\)?[^>]*-->", figure, body)
    body = re.sub(r"</li>(\s*)(<figure\b.*?</figure>)", r"\1\2</li>", body, flags=re.S)
    body = enhance(body, short)
    text, buttons = NEXT[slug]
    btns = "\n".join(f'  <a class="btn {c}" href="{h}">{t}</a>' for c, h, t in buttons)
    body = body.replace('<section class="faq">', f'<div class="next">\n  <p>{text}</p>\n{btns}\n</div>\n\n<section class="faq">', 1)
    body = re.sub(r"(</h1>)", rf'\1\n<p class="byline">By <a href="/">Owen Vogelaar</a>, who maintains Life Dashboard. Updated {date_text(updated)}.</p>', body, count=1)
    first_btn = buttons[0]
    body = re.sub(r'(<p class="byline">.*?</p>\s*<p>.*?</p>)', lambda m: m.group(1) + f'\n<p class="guide-cta"><a class="btn btn-primary btn-store" href="{first_btn[1]}">{first_btn[2]}</a></p>', body, count=1, flags=re.S)
    h1 = strip_tags(re.search(r"<h1>(.*?)</h1>", body, re.S).group(1))
    qa = [(strip_tags(q), strip_tags(a)) for q, a in re.findall(r"<summary>(.*?)</summary>\s*(.*?)</details>", body, re.S)]
    url = f"{BASE}{slug}/"
    graph = [
        {"@type": "TechArticle", "headline": h1, "description": desc, "url": url, "inLanguage": "en",
         "author": {"@id": f"{BASE}#owen"},
         "about": [{"@type": "SoftwareApplication", "@id": f"{BASE}{i}", "name": ENTITY_NAME[i]} for i in GUIDE_ABOUT[slug]],
         "datePublished": UPDATED, "dateModified": updated, "image": f"{BASE}img/social.png",
         "isPartOf": {"@id": f"{BASE}#website"}},
        breadcrumb(short, url),
        ME, WEBSITE,
    ]
    if qa:
        graph.append(faq_entity(qa))
    others = "\n          ".join(
        f'<li><a href="../{g[0]}/"{" aria-current=\"page\"" if g[0] == slug else ""}>{g[1]}</a></li>' for g in GUIDES)
    android = PARTS["android"]
    lead = lead_item("android")
    rest = [it for it in android["get"] if it is not lead]
    main = f"""{nav("../")}

<main id="main">
  <div class="guide-hero"><div class="grid-bg"></div></div>
  <div class="wrap guide-layout">
    <article class="prose">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="../">Life Dashboard</a> / <span aria-current="page">{short}</span></nav>
{body.strip()}
    </article>
    <aside class="aside">
      <div class="box cta">
        <h2>Life Dashboard Companion</h2>
        <p>The open-source Android app this guide uses. No account and no cloud. <a href="../android/">More about the app</a>.</p>
        {lead_button(lead, "../")}
        <p class="aside-alt">{alt_links(rest, "../")}</p>
      </div>
      <nav class="box" aria-label="Guides">
        <h2>Guides</h2>
        <ul>
          {others}
        </ul>
      </nav>
      <div class="box">
        <h2>Products</h2>
        <ul>
          {"".join(f'<li><a href="../{s}/">{PARTS[s]["name"]}</a></li>' for s in ORDER)}
        </ul>
      </div>
    </aside>
  </div>
</main>

{footer("../")}"""
    out = OUT / slug
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page(head(title, desc, url, "../", "article", h1, ld_json(graph)), main, "Guide page of the Life Dashboard site."))
    print(f"guide {slug}: title {len(title)}, description {len(desc)}, faqs {len(qa)}")


# ---------------------------------------------------------------------------------------------
# Products

def guide_card(g, prefix, compact=False):
    slug, name, tag, desc = next(x for x in GUIDES if x[0] == g)
    if compact:
        return f'<a class="guide-link" href="{prefix}{slug}/"><span class="tag">{tag}</span><b>{name}</b></a>'
    return (f'<a class="part" href="{prefix}{slug}/"><span class="tag">{tag}</span><h3>{name}</h3>'
            f'<p>{desc}</p><span class="go">Read the guide</span></a>')


def build_product(slug):
    d = json.loads(tokens((HERE / "products" / f"{slug}.json").read_text()))
    p = PARTS[slug]
    url = f"{BASE}{slug}/"
    prefix = "../"
    lead = lead_item(slug)
    rest = [it for it in p["get"] if it is not lead]
    hero_kind = IMAGES[d["hero_image"]][0]
    highlights = "\n        ".join(
        f'<div class="hl"><h3>{html.escape(h["title"])}</h3><p>{html.escape(h["text"])}</p></div>' for h in d["highlights"])
    rows = []
    for i, s in enumerate(d["sections"]):
        bullets = "\n          ".join(
            f'<li>{b["main"]}' + (f' <span>{b["sub"]}</span>' if b.get("sub") else "") + "</li>" for b in s["bullets"])
        kind = IMAGES[s["image"]][0]
        stage = "purple-glow" if s["image"] in PURPLE else "green-glow"
        tone = " purple" if s["image"] in PURPLE else ""
        media = (f'<div class="show-media{" is-wide" if kind == "wide" else ""}{" has-card" if kind == "card" else ""}"><div class="stage {stage}"></div>'
                 + (f'{image(s["image"], prefix, "p1")}{image(s["image2"], prefix, "p2")}' if s.get("image2") else image(s["image"], prefix, "solo"))
                 + '</div>')
        link = f'<a class="link-arrow" href="{s["link"]["href"]}">{html.escape(s["link"]["text"])}</a>' if s.get("link") else ""
        rows.append(f"""<div class="show{" flip" if i % 2 else ""}" id="{slugify(s["kicker"])}">
      {media}
      <div>
        <div class="kicker{tone}">{html.escape(s["kicker"])}</div>
        <h2>{s["h2"].replace("QR code", "QR&nbsp;code")}</h2>
        <p>{s["text"]}</p>
        <ul class="ticks{" purple-ticks" if tone else ""}">
          {bullets}
        </ul>
        {link}
      </div>
    </div>""")
    faq = "\n      ".join(f'<details{" id=" + chr(34) + f["id"] + chr(34) if f.get("id") else ""}{" open" if f.get("open") else ""}>\n        <summary>{html.escape(f["q"])}</summary>\n        <p>{f["a"]}</p>\n      </details>' for f in d["faq"])
    gl = d.get("guides", [])
    guides = "\n      ".join(guide_card(g, prefix) for g in gl)
    single_label = {"ios": "The payload, step by step (the iPhone app sends the same JSON)",
                    "grafana": "What the stack receives, step by step"}.get(slug, "Step by step")
    single_guide = (f'<p class="faq-more">{single_label}: <a class="link-arrow" href="../{gl[0]}/">{GUIDE_NAMES[gl[0]]}</a></p>' if len(gl) == 1 else "")
    siblings = "\n      ".join(
        f'<a class="part" href="../{s}/"><span class="part-ico">{svg(PARTS[s]["glyph"])}</span><h3>{PARTS[s]["full"]}</h3><p>{PARTS[s]["line"]}</p><span class="go">Learn more</span></a>'
        for s in ORDER if s != slug)
    works_with = {
        "android": 'Sends to <a href="../home-assistant/">the Home Assistant integration</a>, <a href="../grafana/">the Grafana stack</a>, an MQTT broker or any webhook.',
        "ios": 'Sends to <a href="../home-assistant/">the Home Assistant integration</a>, <a href="../grafana/">the Grafana stack</a>, an MQTT broker or any webhook.',
        "home-assistant": 'Pairs with <a href="../android/">Life Dashboard Companion for Android</a> and <a href="../ios/">for iPhone</a>.',
        "grafana": 'Receives from <a href="../android/">Life Dashboard Companion for Android</a> and <a href="../ios/">for iPhone</a>.',
    }[slug]
    entity = ENTITIES[slug]
    compare = ""
    if d.get("compare"):
        c = d["compare"]
        chead = "".join(f'<th scope="col">{h or "Feature"}</th>' for h in c["head"])
        cbody = "".join("<tr><th scope=\"row\">" + r[0] + "</th>" + "".join(f"<td>{x}</td>" for x in r[1:]) + "</tr>" for r in c["rows"])
        compare = f"""<section class="section tight" id="compare">
  <div class="wrap">
    <div class="section-head"><div class="kicker">Compared</div><h2>{c["title"]}</h2><p>{c["intro"]}</p></div>
    <div class="table-wrap compare-wrap" tabindex="0" role="region" aria-label="{html.escape(c["title"])}"><table class="compare"><thead><tr>{chead}</tr></thead><tbody>{cbody}</tbody></table></div>
    <p class="fineprint">{c["source"]}</p>
  </div>
</section>

"""
    commands = ""
    if d.get("commands"):
        commands = (f'<div class="code-window"><div class="code-bar"><i></i><i></i><i></i><span>{html.escape(d["commands"]["title"])}</span></div>'
                    f'<pre tabindex="0"><code>{html.escape(d["commands"]["code"])}</code></pre></div>'
                    f'<p class="fineprint">{d["commands"]["after"]}</p>')
    graph = [breadcrumb(d["nav_name"], url),
             {"@type": "WebPage", "@id": url, "url": url, "name": d["title"], "description": d["description"],
              "about": {"@id": f"{BASE}{ENTITY_ID[slug]}"}, "mainEntity": entity,
              "isPartOf": WEBSITE, "inLanguage": "en", "dateModified": d.get("updated", UPDATED)},
             faq_entity([(f["q"], strip_tags(f["a"])) for f in d["faq"]]), ME,
             {k: v for k, v in PROJECT.items() if k != "hasPart"}]
    PAGE_DATES[f"{slug}/"] = d.get("updated", UPDATED)
    guides_section = f"""<section class="section tight band">
  <div class="wrap">
    <div class="section-head"><div class="kicker">Guides</div><h2>Setup guides</h2></div>
    <div class="family{" three" if len(gl) == 3 else ""}">
      {guides}
    </div>
  </div>
</section>
""" if len(gl) > 1 else ""
    faq_title = {"android": "Questions about the Android app", "ios": "Questions about the iPhone app",
                 "home-assistant": "Questions about the integration", "grafana": "Questions about the stack"}[slug]
    main = f"""{nav(prefix, slug)}

<main id="main">

<section class="hero product-hero">
  <div class="grid-bg"></div>
  <div class="wrap">
    <div>
      <nav class="crumbs" aria-label="Breadcrumb"><a href="../">Life Dashboard</a> / <span aria-current="page">{d["nav_name"]}</span></nav>
      <div class="eyebrow"><span>Open source</span><span>No cloud</span><span>No account</span></div>
      <h1>{html.escape(d["h1"])}</h1>
      <p class="lead">{html.escape(d["lead"])}</p>
      <div class="cta-row stores">
        {lead_button(lead, prefix)}
      </div>
      <p class="fineprint">{alt_links(rest, prefix)}</p>
    </div>
    <div class="product-visual{" is-wide" if hero_kind == "wide" else ""}">
      {image(d["hero_image"], prefix, "hero-shot", eager=True)}
    </div>
  </div>
</section>

<section class="section tight band">
  <div class="wrap">
    <h2 class="sr-only">What it does</h2>
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
      <div class="kicker">Install</div>
      <h2>{p["get_title"]}</h2>
    </div>
    <div class="get-split">
      {get_card(slug, prefix, req=False)}
      <div class="get-side">
        <h3>What you need</h3>
        <p>{d["requirements"]}</p>
        <p class="fineprint">{works_with}</p>
        {commands}
      </div>
    </div>
  </div>
</section>

<section class="section tight" id="faq">
  <div class="wrap">
    <div class="section-head">
      <div class="kicker">FAQ</div>
      <h2>{faq_title}</h2>
    </div>
    <div class="faq">
      {faq}
    </div>
    {single_guide}
  </div>
</section>

{guides_section}
<section class="section tight">
  <div class="wrap">
    <div class="section-head"><div class="kicker">Life Dashboard</div><h2>The other parts</h2><p>Both apps send the same payload, so an Android phone and an iPhone can share one Home Assistant or one stack.</p></div>
    <div class="family three">
      {siblings}
    </div>
  </div>
</section>

</main>

{footer(prefix)}"""
    out = OUT / slug
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page(head(d["title"], d["description"], url, prefix, "website", d["h1"], ld_json(graph)), main, f"Product page: {p['full']}."))
    print(f"product {slug}: title {len(d['title'])}, description {len(d['description'])}, faqs {len(d['faq'])}")


# ---------------------------------------------------------------------------------------------
# Landing page, llms.txt, sitemap, checks

def fill(src, name, content):
    pat = re.compile(rf"(<!-- BUILD:{name} -->).*?(<!-- /BUILD:{name} -->)", re.S)
    new, n = pat.subn(lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}", src)
    assert n >= 1, f"marker {name} not found"
    return new


PROOF = {
    # Update when it changes; the numbers are floors, so they stay true.
    "facts": [("45+", "Android releases since February 2026"), ("3", "outside contributors"), ("4", "parts, all MIT licensed")],
    "projects": [
        ("Health Assistant", "https://github.com/health-assistant-io/health-assistant",
         "A self-hosted health record. Its webhook integration reads the Life Dashboard payload and calls the app \u201cHighly Recommended for Android Users\u201d."),
        ("HealthQuery", "https://github.com/nikira-studio/healthquery",
         "A personal health dashboard in SQLite, with reports and an MCP server. Its data comes from Life Dashboard Companion."),
    ],
}


def proof_section():
    facts = "".join(f"<li><b>{n}</b> {t}</li>" for n, t in PROOF["facts"])
    cards = "\n      ".join(
        f'<a class="part proj" href="{u}"><span class="tag">Built on it</span><h3>{n}</h3><p>{d}</p><span class="go">On GitHub</span></a>'
        for n, u, d in PROOF["projects"])
    cards += (f'\n      <a class="part proj-cta" href="{REPO}/discussions"><span class="tag">Your project</span><h3>Built something on the payload?</h3>'
              f'<p>Tell me in Discussions, and it can join this list.</p><span class="go">Open Discussions</span></a>')
    return f"""<div class="section-head">
      <div class="kicker">In use</div>
      <h2>Other open-source projects build on it</h2>
    </div>
    <ul class="proof-facts">{facts}</ul>
    <div class="family three">
      {cards}
    </div>"""


def build_landing():
    p = OUT / "index.html"
    src = p.read_text()
    src = fill(src, "nav", nav(""))
    src = fill(src, "proof", proof_section())
    src = fill(src, "guides", '<div class="guide-grid">\n      ' + "\n      ".join(guide_card(g[0], "", compact=True) for g in GUIDES) + "\n    </div>")
    src = fill(src, "parts", parts_strip(""))
    src = fill(src, "hero-stores", hero_stores(""))
    src = fill(src, "get", get_section(""))
    if "<!-- BUILD:faq-get -->" in src:
        src = fill(src, "faq-get", f"<p>The Android app: {STATUS_TEXT['android']} The iPhone app: {STATUS_TEXT['ios']} The <a href=\"#get\">install section</a> lists every option.</p>")
    src = fill(src, "footer", footer(""))
    faq = src[src.index('id="faq"'):]
    qa = [(strip_tags(q), strip_tags(a)) for q, a in re.findall(r"<summary>(.*?)</summary>\s*(.*?)</details>", faq, re.S)]
    graph = [WEBSITE, ME, PROJECT] + [ENTITIES[s] for s in ORDER] + [SOURCE_CODE, faq_entity(qa)]
    src = fill(src, "ld", f'<script type="application/ld+json">\n{ld_json(graph)}\n</script>')
    p.write_text(src)
    print(f"landing: faqs {len(qa)}")


def build_hub():
    """The domain root is a hand-written developer page; it only needs to exist."""
    assert (SITE / "index.html").exists(), "site/index.html (the developer page) is missing"


def build_404():
    p = SITE / "404.html"
    pages = [("/life-dashboard/", "Life Dashboard")] + [(f"/life-dashboard/{s}/", PARTS[s]["name"]) for s in ORDER] \
        + [(f"/life-dashboard/{g[0]}/", g[1]) for g in GUIDES] + [("/", "Owen Vogelaar, the developer page"), ("/privacy/", "Privacy")]
    items = "\n".join(f'      <li><a href="{u}">{html.escape(n)}</a></li>' for u, n in pages)
    p.write_text(fill(p.read_text(), "pages", f'<ul class="ticks">\n{items}\n    </ul>'))


def build_llms():
    text = tokens((HERE / "llms.txt.in").read_text())
    for p in (SITE / "llms.txt", OUT / "llms.txt"):
        p.write_text(text)


def build_sitemap():
    urls = [("", UPDATED)] + [(f"{s}/", PAGE_DATES[f"{s}/"]) for s in ORDER] + [(f"{g[0]}/", PAGE_DATES[f"{g[0]}/"]) for g in GUIDES] + [("ios/privacy/", "2026-10-03")]
    lines = f"  <url><loc>{DOMAIN}</loc><lastmod>{UPDATED}</lastmod></url>\n  <url><loc>{DOMAIN}privacy/</loc><lastmod>{UPDATED}</lastmod></url>\n" + "\n".join(f"  <url><loc>{BASE}{u}</loc><lastmod>{d}</lastmod></url>" for u, d in urls)
    (SITE / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{lines}\n</urlset>\n')


def check():
    """Refuse a site that says a live store is still coming, or contains a dash we never use."""
    live = {it["id"] for s in ORDER for it in PARTS[s]["get"] if it["status"] == "live"}
    files = list(OUT.rglob("*.html")) + [SITE / "llms.txt", SITE / "index.html"]
    problems = []
    for f in files:
        t = f.read_text()
        for store, phrases in STALE.items():
            if store in live:
                problems += [f"{f.relative_to(ROOT)}: says '{ph}' but {store} is live" for ph in phrases if ph in t]
        if "\u2014" in t or "\u2013" in t:
            problems.append(f"{f.relative_to(ROOT)}: contains an em or en dash")
    for badge, (fname, _) in BADGES.items():
        if badge in live and not (OUT / "img" / "badges" / fname).exists():
            problems.append(f"{badge} is live but img/badges/{fname} is missing")
    llms = (SITE / "llms.txt").read_text()
    problems += [f"llms.txt: the guide {g[0]} is missing" for g in GUIDES if f"{BASE}{g[0]}/" not in llms]
    if problems:
        sys.exit("build check failed:\n  " + "\n  ".join(problems))


if __name__ == "__main__":
    for s in ORDER:
        build_product(s)
    build_hub()
    for g in GUIDES:
        build_guide(g[0], g[1])
    build_landing()
    build_404()
    build_llms()
    build_sitemap()
    check()
    print("ok")
