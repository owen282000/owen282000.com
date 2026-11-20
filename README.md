# owen282000.com

The website at [owen282000.com](https://owen282000.com/): a short page about the open-source apps I make, and the site of [Life Dashboard](https://owen282000.com/life-dashboard/) with its product pages and guides.

It is plain HTML with one stylesheet, without scripts, web fonts or third-party requests. `site/` is what gets served, and every page in it is generated: change the source in `tools/site/i18n/` and run `python3 tools/site/build.py`.

English is the source language and keeps its addresses. Dutch, German, French, Spanish and Brazilian Portuguese live under `/nl/`, `/de/`, `/fr/`, `/es/` and `/pt-br/`, each page with a canonical to itself, hreflang links to the other languages and a language menu. [tools/site/i18n/README.md](tools/site/i18n/README.md) explains the format and how to translate; the build refuses a site whose languages don't fit together.

The App Links file and the iPhone app's privacy policy stay at [owen282000.github.io](https://github.com/owen282000/owen282000.github.io).
