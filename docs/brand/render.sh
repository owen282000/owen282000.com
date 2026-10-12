#!/usr/bin/env bash
# Renders the developer brand from the HTML sources in this folder:
#   developer-icon.png    512 x 512, 24-bit PNG without transparency (Google Play)
#   developer-header.jpg  4096 x 2304, JPEG under 1 MB (Google Play)
# and from the same sources the developer page's assets in site/:
#   site/favicon.ico, site/img/ov-32.png, ov-68.png, ov-180.png  the ov icon
#   site/img/social.png                                          its share image, 1200 x 630
# Needs Google Chrome and ffmpeg. Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
shot() { "$CHROME" --headless=new --hide-scrollbars --force-device-scale-factor="$3" \
  --window-size="$2" --screenshot="$PWD/$4" "file://$PWD/$1" >/dev/null 2>&1; }

shot developer-icon.html 512,512 1 .icon.png
ffmpeg -loglevel error -y -i .icon.png -pix_fmt rgb24 developer-icon.png
shot developer-header.html 2048,1152 2 .header.png
ffmpeg -loglevel error -y -i .header.png -q:v 3 developer-header.jpg
SITE=../../site
ffmpeg -loglevel error -y -i developer-icon.png -vf scale=48:48 "$SITE/favicon.ico"
for s in 32 68 180; do ffmpeg -loglevel error -y -i developer-icon.png -vf scale=$s:$s -pix_fmt rgb24 "$SITE/img/ov-$s.png"; done
shot hub-social.html 1200,630 1 .social.png
ffmpeg -loglevel error -y -i .social.png -pix_fmt rgb24 "$SITE/img/social.png"
rm -f .icon.png .header.png .social.png
for f in developer-icon.png developer-header.jpg "$SITE/img/social.png"; do
  printf '%s: %s, %s bytes\n' "$f" "$(ffprobe -v error -show_entries stream=width,height,pix_fmt -of csv=p=0 "$f")" "$(stat -f %z "$f")"
done
