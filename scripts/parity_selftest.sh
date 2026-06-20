#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT/scripts/vendor_python.sh"
STARFORGE_BUNDLE_RESOURCES="$ROOT/StarforgeLab/Resources" \
  swift run StarforgeLabParity
