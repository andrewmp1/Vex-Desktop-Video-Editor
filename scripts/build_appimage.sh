#!/usr/bin/env bash
# Build dist/Vex/ with PyInstaller, then wrap it as dist/Vex-<arch>.AppImage.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ARCH="$(uname -m)"
APPDIR="$ROOT/dist/Vex.AppDir"
OUT="$ROOT/dist/Vex-${ARCH}.AppImage"
SKIP_PYINSTALLER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-pyinstaller) SKIP_PYINSTALLER=1 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "AppImage builds are Linux-only." >&2
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

if [[ "$SKIP_PYINSTALLER" -eq 0 ]]; then
  "$PYINSTALLER" --noconfirm --clean "$ROOT/vex.spec"
fi

if [[ ! -x "$ROOT/dist/Vex/Vex" ]]; then
  echo "Missing dist/Vex/Vex. Run without --skip-pyinstaller." >&2
  exit 1
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR"
cp -a "$ROOT/dist/Vex/." "$APPDIR/"
cp "$ROOT/packaging/vex.desktop" "$APPDIR/vex.desktop"
cp "$ROOT/assets/icon.png" "$APPDIR/vex.png"
chmod +x "$APPDIR/Vex"

cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE:$HERE/_internal:$PATH"
cd "$HERE"
exec "$HERE/Vex" "$@"
EOF
chmod +x "$APPDIR/AppRun"

TOOL="$ROOT/build/appimagetool-${ARCH}.AppImage"
if [[ ! -x "$TOOL" ]]; then
  mkdir -p "$ROOT/build"
  url="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
  echo "Downloading $url"
  curl -fsSL -o "$TOOL" "$url"
  chmod +x "$TOOL"
fi

mkdir -p "$ROOT/dist"
export ARCH
export VERSION="${VERSION:-0.1.0}"
export APPIMAGE_EXTRACT_AND_RUN=1
"$TOOL" --no-appstream "$APPDIR" "$OUT"
chmod +x "$OUT"
echo "Wrote $OUT"
