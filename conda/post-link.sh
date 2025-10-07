
#!/usr/bin/env bash
# Safe, fail-soft post-link for macOS/Linux
# Writes logs to $PREFIX/conda-meta/movinglines-postlink.log and ALWAYS exits 0
set -e

LOG="${PREFIX}/movinglines-postlink.log"
mkdir -p "$(dirname "$LOG")" || true
{
  echo "== movinglines post-link: $(date) =="
  echo "PREFIX=$PREFIX"

  # Make console scripts executable if present
  for exe in ml movinglines movinglines-cli ml-movinglines; do
    p="$PREFIX/bin/$exe"
    if [ -f "$p" ]; then
      chmod 0755 "$p" 2>/dev/null || true
      echo "chmod 0755 $p"
    fi
  done

  PY="$PREFIX/bin/python"
  if [ ! -x "$PY" ]; then
    echo "No python at $PY; skipping pip install."
    exit 0
  fi

  # Ensure pip exists (defensive)
  "$PY" -m pip --version >/dev/null 2>&1 || "$PY" -m ensurepip --upgrade >/dev/null 2>&1 || true

  # Install PyPI-only dependency without upgrading conda-managed pkgs
  echo "Installing flightplandb via pip..."
  "$PY" -m pip install --no-input --disable-pip-version-check --no-warn-script-location flightplandb || {
    echo "WARNING: pip install flightplandb failed; leaving package installed. You can run:"
    echo "  $PY -m pip install flightplandb"
  }
 
  # Warn if env is on a noexec mount
  if command -v mount >/dev/null 2>&1; then
    if mount | grep -q " $PREFIX " | grep -q noexec; then
	  echo "WARNING: This conda env appears to be on a 'noexec' filesystem."
	  echo "Entry points may not run. Use 'python -m movinglines' or move the env."
    fi
  fi


  echo "Post-link completed."
} >>"$LOG" 2>&1

# NEVER fail the install
exit 0
