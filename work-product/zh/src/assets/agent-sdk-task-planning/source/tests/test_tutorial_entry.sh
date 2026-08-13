#!/usr/bin/env bash
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; test -f "$R/tutorial.sh"; grep -Fq 'bash tutorial.sh run' "$R/ASSET_GUIDE.md"; bash "$R/tutorial.sh" --help >/dev/null
grep -Fq 'docker build --tag "$IMAGE" "$ROOT"' "$R/tutorial.sh"
