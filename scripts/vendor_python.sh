#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESOURCES="$ROOT/StarforgeLab/Resources"
BUILD="$ROOT/.build/starforge-python-vendor"
PYTHON_TAG="3.12-b9"
PYTHON_ASSET="Python-3.12-macOS-support.b9.tar.gz"
PYTHON_URL="https://github.com/beeware/Python-Apple-support/releases/download/$PYTHON_TAG/$PYTHON_ASSET"

case "$(uname -m)" in
  arm64)
    WHEEL_PLATFORM="macosx_11_0_arm64"
    ;;
  x86_64)
    WHEEL_PLATFORM="macosx_10_13_x86_64"
    ;;
  *)
    echo "unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

mkdir -p "$BUILD" "$RESOURCES/bin" "$RESOURCES/wheels"

if [[ ! -f "$BUILD/$PYTHON_ASSET" ]]; then
  curl -L --fail --retry 3 -o "$BUILD/$PYTHON_ASSET" "$PYTHON_URL"
fi

rm -rf "$BUILD/extract" "$RESOURCES/Python.xcframework"
mkdir -p "$BUILD/extract"
tar -xzf "$BUILD/$PYTHON_ASSET" -C "$BUILD/extract"
cp -R "$BUILD/extract/Python.xcframework" "$RESOURCES/Python.xcframework"

cc -arch arm64 -arch x86_64 \
  -I "$RESOURCES/Python.xcframework/macos-arm64_x86_64/Python.framework/Headers" \
  -F "$RESOURCES/Python.xcframework/macos-arm64_x86_64" \
  -framework Python \
  -Wl,-rpath,@executable_path/../Python.xcframework/macos-arm64_x86_64 \
  -o "$RESOURCES/bin/python3" \
  "$ROOT/StarforgeLab/Support/python_launcher.c"

rm -rf "$RESOURCES/pysite" "$RESOURCES/wheels"
mkdir -p "$RESOURCES/pysite" "$RESOURCES/wheels"
python3 -m pip download \
  --dest "$RESOURCES/wheels" \
  --only-binary=:all: \
  --implementation cp \
  --python-version 312 \
  --abi cp312 \
  --platform "$WHEEL_PLATFORM" \
  numpy==2.4.2 pillow==12.1.0

for wheel in "$RESOURCES"/wheels/*.whl; do
  unzip -q "$wheel" -d "$RESOURCES/pysite"
done

rm -rf "$RESOURCES/engine"
mkdir -p "$RESOURCES/engine"
rsync -a --delete --exclude '__pycache__' "$ROOT/starforge" "$RESOURCES/engine/"
rsync -a --delete --exclude '__pycache__' "$ROOT/tests" "$RESOURCES/engine/"
rsync -a --delete --exclude '__pycache__' "$ROOT/tools" "$RESOURCES/engine/"
rsync -a --delete "$ROOT/.github" "$RESOURCES/engine/" 2>/dev/null || true
cp "$ROOT/README.md" "$ROOT/ARCHITECTURE.md" "$ROOT/pyproject.toml" "$RESOURCES/engine/"

cat > "$RESOURCES/BUILDINFO" <<INFO
python_apple_support=$PYTHON_TAG
wheel_platform=$WHEEL_PLATFORM
numpy=2.4.2
pillow=12.1.0
starforge_commit=$(git -C "$ROOT" rev-parse origin/main)
INFO

PYTHONPATH="$RESOURCES/engine:$RESOURCES/pysite" \
PYTHONDONTWRITEBYTECODE=1 \
"$RESOURCES/bin/python3" - <<'PY'
import platform
import numpy
import PIL
import starforge

print(f"python={platform.python_version()}")
print(f"numpy={numpy.__version__}")
print(f"pillow={PIL.__version__}")
print(f"starforge={starforge.__version__}")
PY
