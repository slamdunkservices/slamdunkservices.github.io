#!/bin/sh
# Quarto post-render hook (declared in _quarto.yml). Runs from the project root after every full render.
# Makes the sitemap advertise the homepage as https://slamdunk.bet/ (its canonical URL) instead of /index.html.
set -e
sitemap="${QUARTO_PROJECT_OUTPUT_DIR:-_site}/sitemap.xml"
[ -f "$sitemap" ] || exit 0
sed -i '' 's#<loc>https://slamdunk.bet/index.html</loc>#<loc>https://slamdunk.bet/</loc>#' "$sitemap"
