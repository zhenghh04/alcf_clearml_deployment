#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${DOWNLOAD_DATA_ROOT:-/eagle/AuroraGPT/hzheng/}"
MATH_REPO="${DOWNLOAD_MATH_REPO:-NVIDIA/Nemotron-Math-v2}"
CODE_REPO="${DOWNLOAD_CODE_REPO:-NVIDIA/Nemotron-Pretraining-Code-v2}"
MODE="${DOWNLOAD_MODE:-both}"

mkdir -p "${DATA_ROOT}"

# If the datasets require auth, export HF_TOKEN before running:
# export HF_TOKEN=your_hf_token

download_repo() {
  local repo="$1"
  python - "$repo" <<'PY'
import os
import sys
import time
from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError

repo = sys.argv[1]
token = os.environ.get("HF_TOKEN")
api = HfApi(token=token)
poll_interval = int(os.environ.get("HF_POLL_INTERVAL_SEC", "600"))
max_attempts_env = os.environ.get("HF_MAX_ATTEMPTS", "")
max_attempts = int(max_attempts_env) if max_attempts_env else None
attempt = 0

while True:
    attempt += 1
    try:
        info = api.dataset_info(repo)
    except HfHubHTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")
        print(f"[download] ERROR: cannot access {repo} (HTTP {status}).")
        print("[download] If this dataset is gated, request access and set HF_TOKEN.")
        if max_attempts and attempt >= max_attempts:
            sys.exit(1)
        print(f"[download] Waiting {poll_interval}s before retry...")
        time.sleep(poll_interval)
        continue
    except Exception as exc:
        print(f"[download] ERROR: failed to query {repo}: {exc}")
        if max_attempts and attempt >= max_attempts:
            sys.exit(1)
        print(f"[download] Waiting {poll_interval}s before retry...")
        time.sleep(poll_interval)
        continue

    gated = getattr(info, "gated", None)
    if gated in ("manual", True) and not token:
        print(f"[download] {repo} is gated and HF_TOKEN is not set.")
        if max_attempts and attempt >= max_attempts:
            sys.exit(1)
        print(f"[download] Waiting {poll_interval}s for approval or token...")
        time.sleep(poll_interval)
        continue
    break
PY

  echo "[download] Dataset -> ${DATA_ROOT}/${repo}"
  huggingface-cli download \
    --repo-type dataset \
    --local-dir "${DATA_ROOT}/${repo}" \
    --local-dir-use-symlinks False \
    "${repo}"
}

case "${MODE}" in
  math)
    download_repo "${MATH_REPO}"
    ;;
  code)
    download_repo "${CODE_REPO}"
    ;;
  both)
    download_repo "${MATH_REPO}" &
    math_pid=$!
    download_repo "${CODE_REPO}" &
    code_pid=$!
    wait "${math_pid}" "${code_pid}"
    ;;
  *)
    echo "ERROR: unknown DOWNLOAD_MODE: ${MODE} (expected: math|code|both)" >&2
    exit 1
    ;;
esac

echo "[download] Done"
