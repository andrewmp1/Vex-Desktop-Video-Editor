# !/bin/bash
set -e

UPSTREAM_REPO="https://github.com/AKMessi/vex.git"
VEX_CORE_DIR="vex_core"

mkdir -p "$VEX_CORE_DIR"
echo "🔄 Syncing vex_core with upstream..."
git clone --depth 1 "$UPSTREAM_REPO" /tmp/temp_vex

cp -rf /tmp/temp_vex/* "$VEX_CORE_DIR/"
rm -rf /tmp/temp_vex

echo "✅ vex_core updated! Run setup.sh again if needed."