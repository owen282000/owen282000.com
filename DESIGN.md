# Life Dashboard site: design direction

> **Owen: please read and confirm.** This file transcribes the direction that already exists in
> the brand files of the Android repository (`life-dashboard-companion-app/docs/brand/*.html`)
> and the decisions of the October 2026 design pass on this site. It adds no new brand values.
> Where the site departs from a brand file, it says so, so you can keep or reverse it.

## Identity

Life Dashboard moves health data from a phone to a server you run. The look says that: a dark,
green-tinted dashboard surface, one green heartbeat line that is measured and sent on, real
screenshots of the app and of the places the data lands, and nothing that pretends to be more
than that.

## Palette (from the brand files)

| Role | Value | Source |
|---|---|---|
| Background | gradient `#14181C` to `#101C1C` (`#171D21` at the top left) | banner.html, family-card.html, how-it-works.html, readme-*.html |
| Icon tile | `#143528` to `#0B1D18` | icon.html |
| Store stage | `#173229`, `#11231E`, `#0C1815` | store-shot.html |
| Heartbeat green | `#30B77E` | every brand file |
| Lighter green, for text | `#6FD7A6` | family-card.html, how-it-works-phone.html |
| Text | `#E8EDEF` | family-card.html, feature-graphic.html |
| Secondary text | `#AEB8BC`, `#B9C2C6` | store-shot.html, banner.html |
| Screen time | accent `#B79BFF` on `#241D38` to `#110F1C` | store-shot.html (`body.purple`) |

The site's stylesheet names screen time purple as `#8B5CF6` with `#B9A2FB` for text, and uses
`#101418` as its page background. Both are already in `site/life-dashboard/site.css`.

## Color roles (decided in this pass)

- **Green is the one accent.** It marks what you can act on (buttons, links, the focus ring,
  the current nav item) and the heartbeat line. Headings, icons, ticks, numbers and borders
  stay neutral.
- **Purple means screen time**, and nothing else.
- **Amber `#F0C674` means pending or a caveat**: "Coming soon" captions, the "Coming" status,
  the brand-note callout.
- **Blue `#41BDF5` is the Health Connect or Apple Health node** in the flow diagram, the store on
  the phone where the data already sits.

Departure to confirm: banner.html colors the second line of the headline green. On the site
the H1 is all one color, so the green heartbeat line under it is the accent.

## Typeface

"Helvetica Neue", Helvetica, Arial, sans-serif, as in every brand file. The site adds system
fallbacks and loads no web fonts (it makes no third-party requests, like the app).

## Grid

The faint green grid of the store art and the banner (`rgba(48,183,126,0.06)` lines, 48 px cells,
faded out with a mask). On the site it appears in one place only: on the stages, the dark
store-art panels that hold a screenshot. It is not behind headlines, page headers or whole
sections (the November 2026 redesign removed it there: a grid behind text read as decoration).

## Identity motif: the heartbeat line

From icon.html: "Heartbeat broadcast: pulse, endpoint dot, and two arcs radiating the signal",
chosen because "the pulse is measured AND published, which is exactly what the app does". On the
landing page the line does that job literally: it runs from the phone to the Home Assistant
dashboard in the hero picture, drawn once on load (the one glow on the site). It appears again,
still, above the closing headline, and it is the app icon wherever the icon appears.

## Imagery

From store-shot.html and feature-graphic.html: real captures only, with made-up data; the
app's own UI fills at least half of every frame; other products appear as labelled panels; generic outlines for
devices, no third-party logos. Store badges are the official artwork, unaltered: a store that is
not live yet shows its badge unlinked in a dashed "Coming soon" frame. HACS, Artifact Hub and
Docker Compose have no store badge, so the site draws them in the same black shape, around the
unaltered HACS, Artifact Hub and Docker logos, with the lettering in Roboto as outlines.
AlternativeTo offers only a blue and a white badge, so the site uses a black copy of their compact
badge: their logo mark and lettering unchanged, the panel black like the others. Every badge
shows at the same visible height, 44px: the files are cropped to the edge of the badge, so one
CSS height fits all. Live badges sit in one row, the coming ones in a row of their own below.

## Shape and depth (November 2026 redesign)

- Radius by role: 10 px for controls and small parts (buttons, icon tiles, tags), 16 px for
  cards, tables and code, 24 px for the stages. No pills: a button has the corner and the 44 px
  height of the store badges it sits next to, so a row of both lines up. Phone frames keep a
  device's corner.
- Boxes are for things you can act on or install: install cards, links to the other parts, the
  closing panel of a guide. Facts, guides, claims and questions are ruled lists, not cards.
- One glow: the heartbeat line in the landing hero. Phones and screenshots get a neutral drop
  shadow; cards and buttons get none and do not lift on hover (the border answers instead).
- Labels in sentence case. No uppercase kickers over headings.
- Icons are drawn by hand on a 24 grid with a 2 px round stroke, the line of the heartbeat mark.
- Two themes from one set of tokens, light and dark, following the reader's system setting.
  Screenshots, device frames and code stay dark in both ("dark islands"), since every capture
  is dark.

## Type

One family (see Typeface), one scale: 13, 14, 15 and 17 px for text (17 is the body), 18 and 24
for small headings, and fluid sizes for H2 (28 to 40 px) and H1 (34 to 56 px). Headings are bold
with tight tracking; body copy stays under 70 characters a line. Secondary text is the muted
ink, never a smaller size alone.

## Layout

- Content width 1200 px with a 32 px gutter (16 px on a phone). Sections are 72 to 120 px apart,
  tight ones 56 to 88 px. A section sits on the page or on a band (one shade off, hairline
  above and below).
- Three compositions, so sections differ: rows (words beside a picture, alternating sides), a
  split (heading left, a ruled list right: questions, guides, privacy facts, highlights) and a
  full-width stage under its words for a dashboard that must be readable.
- A stage shows its screenshot whole, at its own ratio, with room around it. Nothing is cropped
  by a stage, rotated, or laid over something else.
- The landing hero: the headline over the full width, the introduction and the store badges
  side by side under it, then one picture: the phone, the heartbeat line, the Home Assistant
  dashboard. One destination, large enough to read; the others are named in the text. Below
  920 px the dashboard is shown as Home Assistant draws it on a phone, so the pair stays side by
  side down to 320 px.
- Navigation: the brand, the four parts and the guides, then the language, GitHub (an icon) and
  the install button. Below 1040 px the links fold into a menu that also holds the languages; the
  install button stays in the bar.
- Footer: three short columns (the parts, five guides and a link to all of them, docs and
  source), then one small block: the app privacy policies and /legal/, the languages, the
  imprint. Trademark notices and badge credits live on /legal/, not in the footer.

## Dials

ENERGY 2 / RHYTHM 2 / MOTION 1

- ENERGY 2: confident headlines and real screenshots on tinted stages, but one accent.
- RHYTHM 2: rows, splits and at least one full-width stage per page that has a dashboard to show.
- MOTION 1: the heartbeat line draws once, the flow diagram's dots travel twice, then nothing
  moves. Reduced motion turns both off.
