#!/usr/bin/env bash
# Renders the Google Play developer page images from their HTML sources in this folder:
#   developer-icon.png    512 x 512, 24-bit PNG without transparency
#   developer-header.jpg  4096 x 2304, JPEG under 1 MB
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
rm -f .icon.png .header.png
for f in developer-icon.png developer-header.jpg; do
  printf '%s: %s, %s bytes\n' "$f" "$(ffprobe -v error -show_entries stream=width,height,pix_fmt -of csv=p=0 "$f")" "$(stat -f %z "$f")"
done
