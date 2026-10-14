#!/bin/sh
# Publish the site: checks the Quarto version and a clean tree, pushes the render to gh-pages with
# `quarto publish`, then tells IndexNow which pages changed (new URLs or a new <lastmod>, compared with
# the sitemap that was live before this publish). Run from anywhere:  _scripts/publish.sh
set -e
cd "$(dirname "$0")/.."

v=$(quarto --version)
case "$v" in
  1.[0-8].*|0.*) echo "quarto $v is too old; 1.9+ required (see agents.md)" >&2; exit 1 ;;
esac
if [ -n "$(git status --porcelain)" ]; then
  echo "working tree has uncommitted changes; commit first (sitemap lastmod comes from git history)" >&2
  exit 1
fi
if [ "$(git branch --show-current)" = "gh-pages" ]; then
  echo "switch to main before publishing" >&2; exit 1
fi

git fetch -q origin gh-pages
previous=$(mktemp)
trap 'rm -f "$previous"' EXIT
git show origin/gh-pages:sitemap.xml > "$previous" 2>/dev/null || : > "$previous"

quarto publish gh-pages --no-prompt --no-browser

python3 -I _scripts/indexnow.py --previous "$previous" --wait
