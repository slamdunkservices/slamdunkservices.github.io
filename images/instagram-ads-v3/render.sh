#!/usr/bin/env bash
# Render each ad in source.html to a 1080x1350 PNG + JPG.
set -euo pipefail
cd "$(dirname "$0")"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SRC="file://$PWD/source.html"

for n in 01 02 03 04 05 06 07 08 09 10; do
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=1 \
    --virtual-time-budget=8000 \
    --window-size=1080,1350 \
    --screenshot="ad-${n}.png" \
    "${SRC}?only=ad-${n}" >/dev/null 2>&1
  sips -s format jpeg -s formatOptions 88 "ad-${n}.png" --out "ad-${n}.jpg" >/dev/null
  echo "rendered ad-${n}"
done

# contact sheet (rendered with Chrome — no ImageMagick dependency)
"$CHROME" --headless --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=1 --virtual-time-budget=8000 \
  --window-size=1660,1020 \
  --screenshot="contact-sheet.png" \
  "file://$PWD/contact-sheet.html" >/dev/null 2>&1
sips -s format jpeg -s formatOptions 90 contact-sheet.png --out contact-sheet.jpg >/dev/null
echo "rendered contact-sheet"
