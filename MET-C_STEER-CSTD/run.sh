#!/usr/bin/env bash
set -euo pipefail
: "${ANTHROPIC_AUTH_TOKEN:?Export the model gateway token first}"
: "${KGA_MCP_AUTHORIZATION:?Export the complete MCP Authorization value first}"
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
results="${RESULTS_ROOT:-/mnt/d/harbor-kga-results}"
job="${JOB_NAME:-met-c-steer-cstd-$(date +%Y%m%d-%H%M%S)}"
model="${MODEL:-gpt-6.1-sol}"
mkdir -p "$results"
cd "$root"
export UV_NO_SYNC=1
printf 'Results: %s/%s\n' "$results" "$job"
uv run --with harbor-atif2otel harbor run \
    -p "$here" -a claude-code --sm -m "$model" -e docker -n 1 \
    --ak version=2.1.304 \
    --ak "config=$root/KGA_TEST_FILES/images_env/settings.json" \
    --ae 'ANTHROPIC_AUTH_TOKEN=${ANTHROPIC_AUTH_TOKEN}' \
    --ae "ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-http://172.30.251.179:4002}" \
    --ae "ANTHROPIC_DEFAULT_HAIKU_MODEL=$model" \
    --ae "ANTHROPIC_DEFAULT_SONNET_MODEL=$model" \
    --ae "ANTHROPIC_DEFAULT_OPUS_MODEL=$model" \
    --ae 'KGA_MCP_AUTHORIZATION=${KGA_MCP_AUTHORIZATION}' \
    --ae API_TIMEOUT_MS=3000000 \
    --jobs-dir "$results" --job-name "$job" \
    --plugin atif2otel \
    --pk "endpoint=${OTEL_ENDPOINT:-http://localhost:5100}" \
    --pk "experiment_name=${OTEL_EXPERIMENT:-harbor-test-traces}" \
    --pk "output_dir=$results/$job/otel-traces.jsonl" \
    --pk encoding=json
