#!/bin/zsh
# Environment wrapper: throwaway uv env with the harness on PYTHONPATH, run from .code-yash/.
# Usage:
#   dev/py.sh python tests/harness/test_probe.py
#   dev/py.sh inspect eval ...
#   dev/py.sh inspect view --log-dir logs
ROOT="${0:A:h:h}"
export PYTHONPATH="$ROOT/src"
cd "$ROOT" || exit 1
E=()
[ -f "$ROOT/../.env" ] && E=(--env-file "$ROOT/../.env")  # existence test only, never read here
exec uv run -q --no-project $E --with inspect-ai==0.3.282 --with mcp==2.3.0 --with openai==3.35.1 "$@"
