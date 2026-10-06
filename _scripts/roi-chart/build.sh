#!/bin/sh
# Rebuild images/home/cumulative_total.png from the graded ledgers. Run from the repo root.
# Paths and data sources are documented in agents.md ("Update the ROI numbers").
# 2022-23 NBA is scaled from the spreadsheet's flat-stake +929 to the site's +1,610 basis
# (decision 2026-09-14); pass SCALE_2223=1 to draw the raw spreadsheet basis instead.
set -e
tmp="${TMPDIR:-/tmp}/sdb-roi-daily.csv"
/Users/jim/Code/jobs/atp/.venv/bin/python _scripts/roi-chart/ledgers.py "$tmp"
scale="${SCALE_2223:-$(echo "scale=10; 1610/929.0" | bc)}"
Rscript _scripts/roi-chart/chart.R "$tmp" "${1:-images/home/cumulative_total.png}" "$scale"
