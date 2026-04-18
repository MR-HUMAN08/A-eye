#!/usr/bin/env bash
set -euo pipefail

PY=/home/harini/cbit/venv/bin/python
APP=/home/harini/cbit/finpath_data/app/agentic_finpath.py

$PY "$APP" --mode personal_finance --query "If I spend 500 rupees on food delivery today, how does it affect a 5-year house goal?"
$PY "$APP" --mode company_cfo --query "Run a variance-style explanation for rising operating expenses and suggest controls."
$PY "$APP" --mode personal_finance --query "How can I optimize tax under 80C and 80D with moderate risk appetite?"
