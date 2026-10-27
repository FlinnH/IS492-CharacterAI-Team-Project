#!/usr/bin/env bash
# Starts the Character Consistency Workbench (by default at http://127.0.0.1:8492).
# The first run makes app/.venv with the python3 already installed (3.11 or newer)
# and installs app/requirements.txt. Later runs skip pip until requirements.txt changes.
# Once the server answers, it prints the address and opens it in the default
# browser. app/run.sh --no-browser skips the browser.
set -euo pipefail

app_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv="$app_dir/.venv"
stamp="$venv/.requirements.sha256"

# True when the workbench answers at the address given ("http://host:port").
server_answers() {
  python3 -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1] + "/api/health", timeout=1)' "$1" >/dev/null 2>&1
}

# Opens the address in the default browser: open on macOS, wslview on WSL when
# it's there, xdg-open on Linux. Fails when there's no opener or it fails, and
# the caller only changes its words then, so a browser can never stop the server.
open_browser() {
  if [ "$(uname -s)" = "Darwin" ] && command -v open >/dev/null 2>&1; then
    open "$1" >/dev/null 2>&1
  elif grep -qi microsoft /proc/version 2>/dev/null && command -v wslview >/dev/null 2>&1; then
    wslview "$1" >/dev/null 2>&1
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1" >/dev/null 2>&1
  else
    return 1
  fi
}

# Waits until the server answers, then prints the banner and opens the browser
# (unless the third argument is "no"). Gives up quietly when the server process
# ends first, or after about a minute.
open_when_ready() {
  local url="$1" server_pid="$2" browser="$3" tries=0
  until server_answers "$url"; do
    kill -0 "$server_pid" 2>/dev/null || return 0
    tries=$((tries + 1))
    [ "$tries" -lt 120 ] || return 0
    sleep 0.5
  done
  local how="Your browser should open it now. If it doesn't, copy that address into your browser."
  if [ "$browser" = "no" ] || ! open_browser "$url"; then
    how="Open that address in your browser."
  fi
  printf '\n  The workbench is running at %s\n  %s\n  Keep this window open while you use the app.\n  Press Ctrl+C to stop.\n\n' "$url" "$how"
  return 0
}

main() {
  local browser="yes"
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --no-browser) browser="no" ;;
      *)
        echo "run.sh: unknown option \"$1\". Use app/run.sh, or app/run.sh --no-browser." >&2
        exit 2
        ;;
    esac
    shift
  done

  if ! command -v python3 >/dev/null 2>&1; then
    echo "run.sh: python3 not found. Install Python 3.11 or newer, then run this again." >&2
    exit 1
  fi

  local version major rest minor
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

  local wanted
  wanted="$("$venv/bin/python" -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$app_dir/requirements.txt")"
  if [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$wanted" ]; then
    echo "run.sh: installing app/requirements.txt"
    "$venv/bin/python" -m pip install --disable-pip-version-check -r "$app_dir/requirements.txt"
    echo "$wanted" > "$stamp"
  fi

  cd "$app_dir"

  # The address comes from the same settings the server reads. If they can't be
  # read, the server says why in one line below, so skip the browser.
  local address host port url
  if address="$("$venv/bin/python" -c 'from workbench.config import load_settings; s = load_settings(); print(s.workbench_host, s.workbench_port)' 2>/dev/null)"; then
    host="${address% *}"
    port="${address##* }"
    case "$host" in
      0.0.0.0 | :: | localhost) host="127.0.0.1" ;;
      *:*) host="[$host]" ;;
    esac
    url="http://$host:$port"
    if server_answers "$url"; then
      echo "run.sh: the workbench is already running at $url. Open that address in your browser, or press Ctrl+C in the window where it runs to stop it first." >&2
      exit 1
    fi
    # exec below keeps this shell's process ID, so $$ is the server.
    open_when_ready "$url" "$$" "$browser" &
  fi

  exec "$venv/bin/python" -m workbench.main
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
