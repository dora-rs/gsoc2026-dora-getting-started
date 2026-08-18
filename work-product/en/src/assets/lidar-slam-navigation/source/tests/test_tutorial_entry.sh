#!/usr/bin/env bash
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test -f "$R/tutorial.sh"
grep -Fq 'bash tutorial.sh run' "$R/ASSET_GUIDE.md"
grep -Fq SUCCEEDED "$R/ASSET_GUIDE.md"
bash "$R/tutorial.sh" --help >/dev/null
grep -Fxq '.octos-workspace.toml' "$R/.gitignore"
grep -Fxq '.octos/' "$R/.gitignore"
grep -Fxq 'dora/out/' "$R/.gitignore"
grep -Fq 'wait_lifecycle_active /bt_navigator' "$R/tutorial.sh"
grep -Fq "grep -Eq '^active([[:space:]]|$)'" "$R/tutorial.sh"
grep -Fq 'docker build --tag "$IMAGE" "$ROOT"' "$R/tutorial.sh"
