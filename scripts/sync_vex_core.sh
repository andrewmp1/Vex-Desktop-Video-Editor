#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIN_FILE="$ROOT/vex_core.pin"
DEST="$ROOT/vex_core"

if [[ ! -f "$PIN_FILE" ]]; then
  echo "Missing $PIN_FILE" >&2
  exit 1
fi

REPO="$(sed -n 's/^repo=//p' "$PIN_FILE" | head -n1)"
COMMIT="$(sed -n 's/^commit=//p' "$PIN_FILE" | head -n1)"

if [[ -z "$REPO" || -z "$COMMIT" ]]; then
  echo "vex_core.pin must contain repo= and commit=" >&2
  exit 1
fi

echo "Syncing vex_core to $COMMIT"
rm -rf "$DEST"
git clone --filter=blob:none --no-checkout "$REPO" "$DEST"
git -C "$DEST" fetch --depth 1 origin "$COMMIT"
git -C "$DEST" checkout --detach "$COMMIT"
rm -rf "$DEST/.git"

echo "vex_core pinned at $COMMIT"
echo "The desktop UI will pick it up automatically (VEX_AGENT_BACKEND=auto)."
