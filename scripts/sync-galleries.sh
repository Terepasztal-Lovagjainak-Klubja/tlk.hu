#!/usr/bin/env sh
#
# Local entry point for the Drive gallery sync: `pnpm sync:galleries`.
#
# Nobody should have to think about pip to preview a gallery, so this resolves
# the Python side itself. The publish workflow does not use this script — GitHub
# Actions installs the same scripts/requirements.txt through actions/setup-python,
# which caches it.

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
REQUIREMENTS="$ROOT/scripts/requirements.txt"
SCRIPT="$ROOT/scripts/sync_drive_galleries.py"

# Preferred path: uv picks a suitable interpreter and installs the dependencies
# into its own cache. No venv to manage, nothing added to the system Python, and
# it does not go through pip — which matters, because a broken bundled pip is a
# common way for a Homebrew or system Python to fail here.
if command -v uv >/dev/null 2>&1; then
  exec uv run --quiet --python '>=3.10' --with-requirements "$REQUIREMENTS" "$SCRIPT" "$@"
fi

# Fallback: a project-local .venv. Still a venv rather than a global install,
# because installing into the system Python fails outright on most current macOS
# and Linux distributions (PEP 668 "externally-managed-environment").
if ! command -v python3 >/dev/null 2>&1; then
  echo "error: neither uv nor python3 found." >&2
  echo "  Install uv (https://docs.astral.sh/uv/) or Python >= 3.10." >&2
  exit 1
fi

# Checked up front: a 3.9 still ships as /usr/bin/python3 on plenty of machines,
# and finding out after building a venv makes for a confusing failure.
if [ "$(python3 -c 'import sys; print(sys.version_info >= (3, 10))' 2>/dev/null)" != "True" ]; then
  echo "error: python3 is $(python3 --version 2>&1), but gdown needs >= 3.10." >&2
  echo "  Install uv (https://docs.astral.sh/uv/) — it provisions its own Python —" >&2
  echo "  or install Python >= 3.10 (mise.toml pins 3.12)." >&2
  exit 1
fi

VENV="$ROOT/.venv"
STAMP="$VENV/.requirements-stamp"

if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating $VENV ..."
  python3 -m venv "$VENV"
fi

# Reinstall only when requirements.txt actually changed, so the common case is
# just the sync with no dependency work at all.
if [ ! -f "$STAMP" ] || ! cmp -s "$REQUIREMENTS" "$STAMP"; then
  echo "Installing dependencies into $VENV ..."
  if ! "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$REQUIREMENTS"; then
    # Drop the half-built venv so a retry starts clean, then point at the fix.
    venv_python=$("$VENV/bin/python" --version 2>&1 || echo "the venv's Python")
    rm -rf "$VENV" 2>/dev/null || true
    echo "" >&2
    echo "error: pip failed inside $VENV ($venv_python)." >&2
    echo "  That Python probably ships a broken bundled pip." >&2
    echo "  Easiest fix: install uv (https://docs.astral.sh/uv/) and re-run —" >&2
    echo "  this script prefers uv and skips pip entirely." >&2
    exit 1
  fi
  cp "$REQUIREMENTS" "$STAMP"
fi

exec "$VENV/bin/python" "$SCRIPT" "$@"
