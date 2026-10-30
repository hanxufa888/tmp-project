#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p /logs/verifier
printf '0\n' > /logs/verifier/reward.txt
cd /app
if sha256sum --check input.sha256 && python "$here/validate.py"; then
    printf '1\n' > /logs/verifier/reward.txt
else
    echo "Workflow artifact validation failed; inspect verifier logs and collected artifacts." >&2
fi
