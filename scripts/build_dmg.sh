#!/usr/bin/env bash
# Build dist/Vex.app with PyInstaller, then wrap it as dist/Vex.dmg.
# macOS only. create-dmg may exit non-zero on a "blessing" warning; the DMG
# is the success signal.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP="$ROOT/dist/Vex.app"
OUT="$ROOT/dist/Vex.dmg"
SKIP_PYINSTALLER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-pyinstaller) SKIP_PYINSTALLER=1 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "DMG builds are macOS-only." >&2
  exit 1
fi

if [[ -x "$ROOT/.venv/bin/pyinstaller" ]]; then
  PYINSTALLER="$ROOT/.venv/bin/pyinstaller"
elif command -v pyinstaller >/dev/null 2>&1; then
  PYINSTALLER="$(command -v pyinstaller)"
else
  echo "pyinstaller not found. Run: pip install -e \".[dev]\"" >&2
  exit 1
fi

if ! command -v create-dmg >/dev/null 2>&1; then
  echo "create-dmg not found. Run: brew install create-dmg" >&2
  exit 1
fi

if [[ "$SKIP_PYINSTALLER" -eq 0 ]]; then
  "$PYINSTALLER" --noconfirm --clean "$ROOT/vex.spec"
fi

if [[ ! -d "$APP" ]]; then
  echo "Missing dist/Vex.app. Run without --skip-pyinstaller." >&2
  exit 1
fi

mkdir -p "$ROOT/dist"
rm -f "$OUT"

set +e
create-dmg \
  --volname "Vex" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "Vex.app" 200 190 \
  --hide-extension "Vex.app" \
  --app-drop-link 600 185 \
  --no-internet-enable \
  "$OUT" \
  "$APP"
status=$?
set -e

if [[ ! -f "$OUT" ]]; then
  echo "create-dmg exited $status and did not write $OUT" >&2
  exit 1
fi
echo "Wrote $OUT"
