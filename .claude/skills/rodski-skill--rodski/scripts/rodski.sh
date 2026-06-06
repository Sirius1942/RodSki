#!/usr/bin/env bash
set -euo pipefail

RODSKI_BIN="${RODSKI_BIN:-}"
RODSKI_HOME="${RODSKI_HOME:-}"

# Keep RodSki case helper imports from writing __pycache__ into testcase modules.
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"

if [[ -z "$RODSKI_BIN" ]]; then
  for candidate in \
    "$HOME/.local/share/rodski/venv/bin/rodski"
  do
    if [[ -x "$candidate" ]]; then
      RODSKI_BIN="$candidate"
      break
    fi
  done

  if [[ -z "$RODSKI_BIN" ]] && command -v rodski >/dev/null 2>&1; then
    RODSKI_BIN="$(command -v rodski)"
  fi
fi

if [[ -z "$RODSKI_BIN" || ! -x "$RODSKI_BIN" ]]; then
  echo "RodSki CLI not found. Expected $HOME/.local/share/rodski/venv/bin/rodski or a RODSKI_BIN override" >&2
  exit 127
fi

if [[ -z "$RODSKI_HOME" ]]; then
  RODSKI_PY="$(head -n 1 "$RODSKI_BIN" | sed 's/^#!//')"
  if [[ -n "$RODSKI_PY" && -x "$RODSKI_PY" ]]; then
    RODSKI_HOME="$("$RODSKI_PY" - <<'PY' 2>/dev/null || true
import rodski
print(rodski.__path__[0])
PY
)"
  fi
fi

if [[ -n "$RODSKI_HOME" && -d "$RODSKI_HOME" ]]; then
  export PYTHONPATH="$RODSKI_HOME${PYTHONPATH:+:$PYTHONPATH}"
elif [[ -n "$RODSKI_HOME" ]]; then
  echo "Warning: RODSKI_HOME does not exist: $RODSKI_HOME" >&2
fi

exec "$RODSKI_BIN" "$@"
