#!/usr/bin/env bash
# Starts the Character Consistency Workbench (by default at http://127.0.0.1:8492).
# The first run makes app/.venv with the python3 already installed (3.11 or newer)
# and installs app/requirements.txt. Later runs skip pip until requirements.txt changes.
set -euo pipefail

app_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv="$app_dir/.venv"
stamp="$venv/.requirements.sha256"

if ! command -v python3 >/dev/null 2>&1; then
  echo "run.sh: python3 not found. Install Python 3.11 or newer, then run this again." >&2
  exit 1
fi

version="$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
major="${version%%.*}"
rest="${version#*.}"
minor="${rest%%.*}"
case "$major$minor" in
  '' | *[!0-9]*)
    echo "run.sh: could not read the python3 version (got \"$version\")." >&2
    exit 1
    ;;
esac
if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 11 ]; }; then
  echo "run.sh: python3 is $version, and the workbench needs 3.11 or newer." >&2
  exit 1
fi

if [ ! -x "$venv/bin/python" ]; then
  echo "run.sh: creating app/.venv with Python $version"
  python3 -m venv "$venv"
fi

wanted="$("$venv/bin/python" -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$app_dir/requirements.txt")"
if [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$wanted" ]; then
  echo "run.sh: installing app/requirements.txt"
  "$venv/bin/python" -m pip install --disable-pip-version-check -r "$app_dir/requirements.txt"
  echo "$wanted" > "$stamp"
fi

cd "$app_dir"
exec "$venv/bin/python" -m workbench.main
