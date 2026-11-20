# Translating the site

The site is built from `tools/site/i18n/<lang>/`. English (`en/`) is the source and keeps its
addresses. Every other language is a folder next to it, and its pages are served under
`/<lang>/`: `/de/life-dashboard/android/` is the German `/life-dashboard/android/`.

| Language | Folder | Served at | hreflang |
|---|---|---|---|
| English | `en/` | `/` | `en` (and `x-default`) |
| Dutch | `nl/` | `/nl/` | `nl` |
| German | `de/` | `/de/` | `de` |
| French | `fr/` | `/fr/` | `fr` |
| Spanish | `es/` | `/es/` | `es` |
| Portuguese (Brazil) | `pt-br/` | `/pt-br/` | `pt-BR` and `pt` |

Portuguese is Brazilian: Brazil brings more search impressions, more visits and more buyers than
Portugal, and both apps ship `pt-BR` strings. The page also answers for `pt`, so a reader in
Portugal gets it instead of English.

## What one language consists of

Work only inside your own folder. Never edit `en/`, another language, `build.py` or the
stylesheet: five translators work at the same time. If the English text looks wrong, report it.

```
tools/site/i18n/<lang>/
  lang.json            the language itself; set "complete": true when you are done
  strings.json         everything the templates say (copy en/strings.json and translate the values)
  pages/hub.html       /                      the developer page
  pages/privacy.html   /privacy/              the site's privacy notice
  pages/landing.html   /life-dashboard/       the landing page
  pages/ios-privacy.html  /life-dashboard/ios/privacy/
  products/android.json, ios.json, home-assistant.json, grafana.json
  guides/<id>.html     23 guides, the same file names as in en/guides/
```

That is 32 pages: 4 in `pages/`, 4 products, 23 guides and the guide index
(`/life-dashboard/guides/`), which has no file of its own and is made from `strings.json`.
`lang.json` already exists for every language (folder, hreflang, month names, date pattern);
change it only to set `complete`.

File names are the page ids and stay English in every language. A page exists in your language
as soon as its file does; until then links to it lead to the English page.

## The build and the check

```
cp ~/Projects/LifeDashboard/owen282000.com/tools/site/stats.json tools/site/   # once, never commit it
/opt/homebrew/bin/python3 tools/site/build.py               # builds; lists what is still to translate
/opt/homebrew/bin/python3 tools/site/build.py --strict de   # fails on anything German still lacks
```

Run the plain build while you work: it builds whatever exists and reports the rest as notes.
Run `--strict <lang>` before you finish. It must end with `ok`. Then set `"complete": true` in
your `lang.json`, after which the plain build holds your language to the same standard.

The check fails on:

- a page of your language that is missing, or a key missing from your `strings.json`
- hreflang that is not mutual, a wrong canonical or `<html lang>` (the build writes these, so
  this only fails if a file is in the wrong place)
- a link from a translated page to an English page that has a translation
- a link with a `#fragment` that does not exist on the page it leads to
- a title or description that another page already uses, or that is still the English one
- a translation whose code blocks, screenshots, tables, ids or links to pages of this site
  differ from the English file (for a product: images, code, the number of bullets, FAQ ids)
- an em dash or en dash anywhere, a leftover `{{...}}` token

It also notes titles over 65 and descriptions over 165 characters.

Commit only `tools/site/i18n/<lang>/`. Leave the generated `site/` out of your commit (`git
checkout -- site && git clean -fdq site` after your last build): every language changes the
English pages too (their language menu and hreflang links gain it) and `site/sitemap.xml`, so
five translators committing `site/` would collide. Whoever merges the languages builds once and
commits `site/` then. Never commit `tools/site/stats.json`.

German starts with two guides (`guides/health-connect-home-assistant.html` and
`guides/health-connect-webhook.html`) and a `strings.json` that holds only the words those two
needed; everything else in it is still to add.

## What to translate, and what to leave exactly as it is

Translate: all prose, headings, table cells, FAQ questions and answers, `title:` and
`description:` in a file's header, alt texts and button labels in `strings.json`.

Leave untouched:

- **File structure.** Same elements in the same order as the English file: every `<h2>`, list,
  table row, `<details>`, `<!-- IMG: ... -->` comment and `<!-- BUILD:name -->` marker. The
  build gives your headings the ids of the English headings by position, so `#set-it-up` is
  the same section in every language. That only works when the headings match one to one.
- **`<h2>FAQ</h2>`.** Keep it literally; the build writes the heading in your language
  (`ui.faq`).
- **Links.** Keep every `href` as written (`../android/#get`, `/life-dashboard/ios/`). The
  build points it at the page in your language, and at the English page (marked
  `hreflang="en"`) while yours does not exist. Never write `/de/...` yourself. An external
  link may go to the same document in your language when one exists (a vendor's help page).
- **Code.** Everything inside `<pre><code>` and `<code>`, JSON keys and values, entity ids such
  as `sensor.pixel_8_steps_today`, URLs, header names, file names, commands. Comments inside
  code stay English too: the check compares code blocks byte for byte.
- **Tokens and placeholders.** `{{status:android}}`, `{{status:ios}}`, `{{play_url}}` in pages,
  and `{date}`, `{n}`, `{name}`, `{pitch}`, `{discussions}`, `{android}`, `{ios}` in
  `strings.json`. Keep them, move them where your grammar needs them.
- **Entities.** `&nbsp;`, `&#8209;` (the hyphen in F&#8209;Droid that must not break), `&gt;`,
  `&amp;`.
- **Names.** Life Dashboard, Life Dashboard Companion, Home Assistant, Health Connect, Apple
  Health, Apple Watch, Samsung Health, Galaxy Watch, Google Health, Fitbit, Pixel Watch, Garmin
  Connect, Oura, Withings, Grafana, Postgres, MQTT, HACS, Marketplace, Obtainium, F-Droid,
  Google Play, App Store, GitHub, n8n, Node-RED, MCP, Docker Compose, Helm, Xcode, TestFlight,
  and every other product, company and person. Also the technical words people search for in
  English everywhere: webhook, payload, backfill (explain it once, then use it), QR code,
  sensor, dashboard, API, JSON, HMAC.
- **Prices and versions.** €4.99 and €6.99 once (US$4.99, US$5.99), version numbers, counts
  (34 types, 28 types, 36 sensors), dates of facts. Write the price the way your language does
  (`4,99&nbsp;€` in German, `€ 4,99` in Dutch, `R$` never: the store sets local prices, so keep
  the euro and dollar figures).
- **`updated:`** in a header: copy the English date. Add `published: 2026-11-20` (the day the
  translation appears) to every guide.
- **JSON keys and structure** in `products/*.json` and `strings.json`: translate values only.
  In a product file, leave `hero_image`, `image`, `image2`, `code`, `id`, `open`, `guides`,
  `updated` and every `href` alone. In `strings.json`, a guide's `buttons` is a list of
  labels, in the order of the English list.

### Labels of the apps

A label the reader has to find on a screen (`<strong>Sync Now</strong>`,
`<strong>Send history</strong>`, `<strong>What to send</strong>`) must be the label the app
shows in your language, not your own translation. Look each one up:

- Android: `~/Projects/LifeDashboard/life-dashboard-companion-app/app/src/main/res/values-<lang>/strings.xml`
  (`values-nl`, `values-de`, `values-fr`, `values-es`, `values-pt-rBR`); find the English
  label in `values/strings.xml`, take the same `name` from your language's file.
- iPhone: the String Catalogs in `~/Projects/LifeDashboard/life-dashboard-companion-ios/`
  (`LifeDashboardCompanion/Localizable.xcstrings`, `InfoPlist.xcstrings`,
  `AppShortcuts.xcstrings`, `LifeDashboardWidget/Localizable.xcstrings`).
- Home Assistant (`Settings > Devices & services > Add integration`): Home Assistant's own
  wording in your language.
- Other apps (Samsung Health, Garmin Connect, the iPhone's Settings): their own wording in your
  language when you are certain of it; otherwise keep the English label.

When an app has no translation for a label, keep the English label. Never invent one. The
screenshots show the English apps; that is fine.

## Tone

The English text is plain and exact: short sentences, the reader addressed directly, no sales
language, no exclamation marks, nothing claimed that the app does not do. Keep that. Write as a
native speaker would write a good technical guide, not as a translation: restructure a sentence
when your language wants it, keep the meaning and every fact.

| Language | Address the reader as | Notes |
|---|---|---|
| Dutch | je, jij | "je" throughout, no "u". Compound words written as one. Keep English tech words Dutch readers use (sync, dashboard, backfill, webhook). |
| German | du | As in the two existing German guides, which set the style. Compounds with a product name take hyphens (Home-Assistant-Integration, Health-Connect-Daten). Typographic quotes „ “. |
| French | vous | Space before `:` `;` `?` `!` as a non-breaking space (`&nbsp;`), guillemets « » with `&nbsp;` inside. "Application", not "appli". |
| Spanish | tú | Neutral international Spanish that reads well in Spain and Latin America. Opening `¿` and `¡`. |
| Portuguese (Brazil) | você | Brazilian spelling and vocabulary (celular, aplicativo, tela, baixar). |

Rules that hold in every language, because the site's build enforces them or Owen asks for them:

- Never an em dash or en dash. Use a comma, a colon, or two sentences.
- A heading or title never ends with a full stop.
- No AI-sounding filler ("in today's world", "seamlessly", "unlock").
- "Open source", "no account", "no cloud", "pay once, no subscription" are the claims that
  matter. Translate them the way people in your language actually say them.

## Search: write the title and description for your language

Do not translate `title:` and `description:` word for word. They decide whether someone
clicks.

- Find what people type in your language. The product names are the same everywhere
  ("samsung health home assistant", "health connect home assistant", "fitbit home assistant"
  are searched in those words in every country), the words around them are not: German uses
  "Gesundheitsdaten", "Daten exportieren", "Bildschirmzeit", "Schlafphasen". Check with a
  search engine's suggestions in your language and country before you choose.
- Put the main query at the start of the title, in the words people type. Keep
  `| Life Dashboard` at the end where the English title has it. Aim for 60 characters or
  fewer; the description 150 to 160, a full sentence that says what the reader gets.
- The header lines `primary query:` and `secondary queries:` are notes for the next writer:
  replace them with the queries you chose for your language.
- The `<h1>` is the question a person would ask, in your language. The first paragraph answers
  it at once; keep that order.
- Every title and description must be unique across the whole site, in every language. The
  check enforces it.

### Addresses

A translated page keeps the English address under its language folder unless you give a guide
a local slug: add `slug: bildschirmzeit-home-assistant` to the guide's header. Do that only
where the English words in the address are not what people in your language type; product
names stay as they are. Lowercase ASCII letters, digits and hyphens. Decide once per guide:
after the page is live its address must not change. Products, the landing page, the index and
the privacy pages always keep their address. Whatever the slug, the file name stays the English
id.

The two existing German guides keep their addresses (`home-assistant-gesundheitsdaten`,
`health-connect-daten-exportieren`); their old addresses under `/life-dashboard/de/` redirect.
They were written in German rather than translated, so their headers say `structure: own`,
which exempts them from the comparison with the English file. Do not use that for new pages.

## The guide template

Every guide in every language gets the same page from the same few elements, so a guide file
holds content only:

```html
<!--
title: ...
description: ...
primary query: ...
secondary queries: ...
updated: 2026-11-09
published: 2026-11-20
-->

<h1>The question</h1>
<p>The answer, in one or two paragraphs.</p>
<p class="flow-line"><span>Watch</span><span>Health Connect</span><span>Home Assistant</span></p>

<h2>A section</h2>
<ol><li>A step</li></ol>            numbered steps, joined by a line
<p class="note">...</p>             a neutral callout; also class="tip" (green) and "warn" (amber)
<table>...</table>                  scrolls sideways on a phone, first column stays in view
<pre><code>...</code></pre>         code, dark in both themes
<!-- IMG: what it shows (A1-health.png) -->   a screenshot from site/life-dashboard/img/

<section class="faq">
  <h2>FAQ</h2>
  <details><summary>Question</summary><p>Answer</p></details>
</section>
```

The build adds the breadcrumb, the byline with the date and reading time, the first button, "On
this page", the closing panel with the store badge and price, related guides, the language
menu and the structured data (TechArticle, BreadcrumbList, FAQPage). Their words come from
`strings.json`: `guides.<id>.name` and `.desc` (lists and cards), `.next` (the sentence in the
closing panel) and `.buttons`.

There is no copy button on code blocks: the site runs no script at all (its
Content-Security-Policy forbids it), and that promise is worth more than the button.

## llms.txt

`llms.txt` stays one English file. The proposal has no per-language form, assistants ask for
it at the root, and they translate for their reader themselves.
