#!/bin/sh
# Quarto post-render hook (declared in _quarto.yml). Runs from the project root after every full render.
# Makes the sitemap advertise index pages by their folder (https://slamdunk.bet/, /nba/, ...) to match the
# canonical tags, instead of .../index.html.
set -e
sitemap="${QUARTO_PROJECT_OUTPUT_DIR:-_site}/sitemap.xml"
[ -f "$sitemap" ] || exit 0
sed -i '' 's#/index\.html</loc>#/</loc>#' "$sitemap"
