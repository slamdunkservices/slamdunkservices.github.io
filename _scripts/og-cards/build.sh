#!/bin/sh
# Renders one 1200x630 social card per row of cards.tsv into images/og/<slug>.png, using the template in
# _og/card.html and headless Chrome (the only rasterizer on this machine). Run from the repo root:
#   _scripts/og-cards/build.sh            # every card
#   _scripts/og-cards/build.sh faq about  # just these slugs
# Chrome often hangs after writing the file, so each run is killed once the PNG appears. Reference the
# output from a page as `image: /images/og/<slug>.png` with an `image-alt`.
set -e
root=$(cd "$(dirname "$0")/../.." && pwd)
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
tsv="$root/_scripts/og-cards/cards.tsv"
template="$root/_og/card.html"
logo="file://$root/images/brand/logo-horizontal-dark.svg"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

esc() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

grep -v '^#' "$tsv" | while IFS="$(printf '\t')" read -r slug title stat sub foot; do
  [ -n "$slug" ] || continue
  if [ $# -gt 0 ]; then
    case " $* " in *" $slug "*) ;; *) continue ;; esac
  fi
  html="$work/$slug.html"
  out="$root/images/og/$slug.png"
  sed -e "s|{{LOGO}}|$logo|" -e "s|{{TITLE}}|$(esc "$title")|" -e "s|{{STAT}}|$(esc "$stat")|" \
      -e "s|{{SUB}}|$(esc "$sub")|" -e "s|{{FOOT}}|$(esc "$foot")|" "$template" > "$html"
  rm -f "$out"
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --user-data-dir="$work/profile-$slug" --window-size=1200,630 --screenshot="$out" "file://$html" \
    >/dev/null 2>&1 &
  pid=$!
  i=0
  while [ ! -s "$out" ] && [ $i -lt 40 ]; do sleep 0.5; i=$((i + 1)); done
  sleep 1
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  if [ -s "$out" ]; then echo "wrote images/og/$slug.png"; else echo "FAILED $slug" >&2; fi
done
