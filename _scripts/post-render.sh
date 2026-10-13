#!/bin/sh
# Quarto post-render hook (declared in _quarto.yml). Runs from the project root after every full render.
#
# 1. Makes the sitemap advertise index pages by their folder (https://slamdunk.bet/, /nba/, ...) to match the
#    canonical tags, instead of .../index.html.
# 2. Replaces every <lastmod> with the date of the last git commit that touched the page's source .qmd.
#    Quarto writes the render time, which marks every page as modified on every publish and teaches search
#    engines to ignore the field. A source with uncommitted changes keeps the render time.
set -e
sitemap="${QUARTO_PROJECT_OUTPUT_DIR:-_site}/sitemap.xml"
[ -f "$sitemap" ] || exit 0
sed -i '' 's#/index\.html</loc>#/</loc>#' "$sitemap"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
site_url="https://slamdunk.bet"
tmp="$sitemap.tmp"
: > "$tmp"
loc=""
while IFS= read -r line; do
  case "$line" in
    *"<loc>"*)
      loc=$(printf '%s' "$line" | sed -e 's#.*<loc>##' -e 's#</loc>.*##')
      ;;
    *"<lastmod>"*)
      path="${loc#"$site_url"/}"
      case "$path" in
        "")  src="index.qmd" ;;
        */)  src="${path}index.qmd" ;;
        *)   src="${path%.html}.qmd" ;;
      esac
      if [ -f "$src" ] && [ -z "$(git status --porcelain -- "$src")" ]; then
        stamp=$(git log -1 --format=%cI -- "$src")
        if [ -n "$stamp" ]; then
          indent=$(printf '%s' "$line" | sed 's#<lastmod>.*##')
          line="${indent}<lastmod>${stamp}</lastmod>"
        fi
      fi
      ;;
  esac
  printf '%s\n' "$line" >> "$tmp"
done < "$sitemap"
mv "$tmp" "$sitemap"
