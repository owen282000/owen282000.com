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

The faint green grid of the store art and the banner (`rgba(48,183,126,0.05)` to `0.06` lines, 46 to
60 px cells, faded out with a mask). On the site it sits behind the heroes and the screenshot
stages, never as a page-wide pattern.

## Identity motif: the heartbeat line

From icon.html: "Heartbeat broadcast: pulse, endpoint dot, and two arcs radiating the signal",
chosen because "the pulse is measured AND published, which is exactly what the app does". The site draws it
once under the landing H1 (the one glow on that screen), again, still, above the closing
headline, and it is the app icon wherever the icon appears.

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

## Shape and depth (decided in this pass)

- Radius scale, by role: 10 px small parts, 16 px cards, boxes, code and tables, 24 px large
  stages, pill for buttons and chips. Phone frames keep a device's corner.
- One glow per screen: the heartbeat line in the hero, the app node in the flow diagram.
  Phones and screenshots get a neutral drop shadow.
- Labels in sentence case. No uppercase kickers over headings.
- Icons are drawn by hand on a 24 grid with a 2 px round stroke, the line of the heartbeat mark.
- Dark only: every brand asset and every screenshot is dark. The app ships light, dark and
  system; a light site would start with tokens for both modes and screenshots that suit both.

## Dials

ENERGY 2 / RHYTHM 2 / MOTION 1

- ENERGY 2: confident headlines and real screenshots on tinted stages, but one accent.
- RHYTHM 2: zigzag rows with at least one full-width break per page (the Grafana screenshot on
  the landing page, a stacked row on every product page).
- MOTION 1: the heartbeat draws once, the flow diagram's dots travel twice, then nothing moves.
  Reduced motion turns both off.
