#!/usr/bin/env bash
set -euo pipefail

SRC_ENDPOINT="${GLOBUS_SRC_ENDPOINT:-alcf#dtn_eagle}"
DST_ENDPOINT="${GLOBUS_DST_ENDPOINT:-alcf#dtn_flare}"
SRC_PATH="${TRANSFER_SRC_PATH:-/eagle/AuroraGPT/hzheng/datasets}"
DST_PATH="${TRANSFER_DST_PATH:-/flare/AuroraGPT/hzheng/datasets}"
RECURSIVE="${TRANSFER_RECURSIVE:-1}"
POLL_INTERVAL="${TRANSFER_POLL_INTERVAL:-30}"
SYNC_LEVEL="${TRANSFER_SYNC_LEVEL:-checksum}"
LABEL="${TRANSFER_LABEL:-auroragpt-7b-tokenized-transfer}"

usage() {
  cat <<'USAGE'
Usage: transfer_tokenized_to_aurora.sh [options]

Options:
  --src-endpoint NAME   Source Globus endpoint (default: alcf#dtn_eagle)
  --dst-endpoint NAME   Destination Globus endpoint (default: alcf#dtn_flare)
  --src-path PATH       Source path (default: /eagle/AuroraGPT/hzheng/datasets)
  --dst-path PATH       Destination path (default: /flare/AuroraGPT/hzheng/datasets)
  --recursive 0|1       Recursive transfer (default: 1)
  --poll-interval SEC   Poll interval in seconds (default: 30)
  --sync-level LEVEL    Globus sync level (default: checksum)
  --label TEXT          Transfer label
  -h, --help            Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src-endpoint)
      SRC_ENDPOINT="$2"; shift 2 ;;
    --dst-endpoint)
      DST_ENDPOINT="$2"; shift 2 ;;
    --src-path)
      SRC_PATH="$2"; shift 2 ;;
    --dst-path)
      DST_PATH="$2"; shift 2 ;;
    --recursive)
      RECURSIVE="$2"; shift 2 ;;
    --poll-interval)
      POLL_INTERVAL="$2"; shift 2 ;;
    --sync-level)
      SYNC_LEVEL="$2"; shift 2 ;;
    --label)
      LABEL="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v globus >/dev/null 2>&1; then
  echo "ERROR: globus CLI not found in PATH." >&2
  exit 1
fi

recursive_flag=()
if [[ "${RECURSIVE}" == "1" ]]; then
  recursive_flag+=(--recursive)
fi

echo "[transfer] src=${SRC_ENDPOINT}:${SRC_PATH}"
echo "[transfer] dst=${DST_ENDPOINT}:${DST_PATH}"
echo "[transfer] poll_interval=${POLL_INTERVAL} sync_level=${SYNC_LEVEL}"

python ../multi_facilities/tasks/transfer_globus.py \
  --src-endpoint "${SRC_ENDPOINT}" \
  --dst-endpoint "${DST_ENDPOINT}" \
  --src-path "${SRC_PATH}" \
  --dst-path "${DST_PATH}" \
  --label "${LABEL}" \
  --poll-interval "${POLL_INTERVAL}" \
  --sync-level "${SYNC_LEVEL}" \
  "${recursive_flag[@]}"

echo "[transfer] Done"
