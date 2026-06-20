#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="StarforgeLab"
BUNDLE="$ROOT/dist/$APP_NAME.app"
EXECUTABLE="$ROOT/.build/debug/$APP_NAME"

cd "$ROOT"

pkill -x "$APP_NAME" 2>/dev/null || true
swift build --product "$APP_NAME"

rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/Contents/MacOS" "$BUNDLE/Contents/Resources"
cp "$EXECUTABLE" "$BUNDLE/Contents/MacOS/$APP_NAME"
if [[ -d "$ROOT/StarforgeLab/Resources/Python.xcframework" ]]; then
  rsync -a --delete "$ROOT/StarforgeLab/Resources/" "$BUNDLE/Contents/Resources/"
fi

cat > "$BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>$APP_NAME</string>
  <key>CFBundleIdentifier</key>
  <string>app.starforge.lab</string>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>14.0</string>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
PLIST

if [[ "${1:-}" == "--verify" ]]; then
  STARFORGE_ENGINE_ROOT="$ROOT" "$BUNDLE/Contents/MacOS/$APP_NAME" &
  sleep 2
  pgrep -x "$APP_NAME" >/dev/null
else
  /usr/bin/open -n "$BUNDLE"
fi
