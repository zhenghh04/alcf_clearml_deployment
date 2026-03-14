#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

DATA_ROOT="${DOWNLOAD_DATA_ROOT:-/eagle/AuroraGPT/hzheng/datasets}"
REPO_ID="${DOWNLOAD_DOLMA_REPO:-allenai/dolma}"
REVISION="${DOWNLOAD_DOLMA_REVISION:-main}"
DOLMA_VERSION="${DOWNLOAD_DOLMA_VERSION:-v1_7}"
ALLOW_PATTERNS="${DOWNLOAD_ALLOW_PATTERNS:-urls/${DOLMA_VERSION}.txt}"
IGNORE_PATTERNS="${DOWNLOAD_IGNORE_PATTERNS:-}"
LOCAL_DIR="${DOWNLOAD_LOCAL_DIR:-}"
FULL_DOWNLOAD="${DOWNLOAD_DOLMA_FULL:-1}"
FULL_OUTPUT_DIR="${DOWNLOAD_DOLMA_FULL_OUTPUT_DIR:-}"
DOWNLOADER="${DOWNLOAD_DOLMA_DOWNLOADER:-auto}"
ARIA_CONNECTIONS="${DOWNLOAD_DOLMA_ARIA_CONNECTIONS:-16}"
BY_CORPUS_SUBDIR="${DOWNLOAD_DOLMA_BY_CORPUS_SUBDIR:-1}"
WGET_JOBS="${DOWNLOAD_DOLMA_WGET_JOBS:-8}"
NUM_WORKERS="${DOWNLOAD_DOLMA_NUM_WORKERS:-}"

usage() {
  cat <<'USAGE'
Usage: download_dolma_v1.7.sh [options]

Options:
  --data-root PATH         Output root (default: /eagle/AuroraGPT/hzheng/datasets)
  --repo-id NAME           HF dataset repo id (default: allenai/dolma)
  --revision REV           HF revision/tag/branch (default: main)
  --dolma-version NAME     Dolma version manifest under urls/ (default: v1_7)
  --allow-patterns CSV     Comma-separated allow patterns for snapshot_download
  --ignore-patterns CSV    Comma-separated ignore patterns for snapshot_download
  --local-dir PATH         Explicit destination directory
  --full                   Download full shard data from manifest URLs (default: on)
  --full-output-dir PATH   Where to store full shard files
  --downloader NAME        auto|aria2c|wget (default: auto)
  --aria-connections N     aria2c -x/-s value (default: 16)
  --by-corpus-subdir 0|1   Store full download under corpus subfolders (default: 1)
  --num-workers N          Alias for downloader parallelism (sets both wget-jobs and aria-connections)
  --wget-jobs N            Parallel jobs for wget mode (default: 8)
  -h, --help               Show this help

Environment:
  HF_TOKEN                 Optional Hugging Face token for gated/private access
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-root)
      DATA_ROOT="$2"; shift 2 ;;
    --repo-id)
      REPO_ID="$2"; shift 2 ;;
    --revision)
      REVISION="$2"; shift 2 ;;
    --dolma-version)
      DOLMA_VERSION="$2"; shift 2 ;;
    --allow-patterns)
      ALLOW_PATTERNS="$2"; shift 2 ;;
    --ignore-patterns)
      IGNORE_PATTERNS="$2"; shift 2 ;;
    --local-dir)
      LOCAL_DIR="$2"; shift 2 ;;
    --full)
      FULL_DOWNLOAD=1; shift ;;
    --full-output-dir)
      FULL_OUTPUT_DIR="$2"; shift 2 ;;
    --downloader)
      DOWNLOADER="$2"; shift 2 ;;
    --aria-connections)
      ARIA_CONNECTIONS="$2"; shift 2 ;;
    --by-corpus-subdir)
      BY_CORPUS_SUBDIR="$2"; shift 2 ;;
    --num-workers)
      NUM_WORKERS="$2"; shift 2 ;;
    --wget-jobs)
      WGET_JOBS="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${LOCAL_DIR}" ]]; then
  LOCAL_DIR="${DATA_ROOT}/${REPO_ID}/${DOLMA_VERSION}"
fi
if [[ -z "${FULL_OUTPUT_DIR}" ]]; then
  FULL_OUTPUT_DIR="${DATA_ROOT}/${REPO_ID}/${DOLMA_VERSION}"
fi
if [[ -n "${NUM_WORKERS}" ]]; then
  ARIA_CONNECTIONS="${NUM_WORKERS}"
  WGET_JOBS="${NUM_WORKERS}"
fi

mkdir -p "${LOCAL_DIR}"
echo "[download] repo=${REPO_ID} revision=${REVISION} dolma_version=${DOLMA_VERSION}"
echo "[download] local_dir=${LOCAL_DIR}"

python - "$REPO_ID" "$REVISION" "$LOCAL_DIR" "$ALLOW_PATTERNS" "$IGNORE_PATTERNS" "$DOLMA_VERSION" <<'PY'
import os
import sys

from huggingface_hub import snapshot_download
from huggingface_hub.errors import RevisionNotFoundError


def split_csv(value: str):
    value = value.strip()
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


repo_id = sys.argv[1]
revision = sys.argv[2]
local_dir = sys.argv[3]
allow_patterns = split_csv(sys.argv[4])
ignore_patterns = split_csv(sys.argv[5])
dolma_version = sys.argv[6]
token = os.environ.get("HF_TOKEN")

try:
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        local_dir=local_dir,
        token=token,
        allow_patterns=allow_patterns,
        ignore_patterns=ignore_patterns,
    )
except RevisionNotFoundError as exc:
    if repo_id == "allenai/dolma":
        raise SystemExit(
            f"{exc}\nHint: use --revision main (Dolma v1.7 manifest is urls/{dolma_version}.txt)."
        )
    raise
PY

if [[ "${FULL_DOWNLOAD}" != "1" ]]; then
  echo "[download] Done"
  exit 0
fi

manifest_file="${LOCAL_DIR}/urls/${DOLMA_VERSION}.txt"
if [[ ! -f "${manifest_file}" ]]; then
  echo "ERROR: manifest not found: ${manifest_file}" >&2
  exit 1
fi

mkdir -p "${FULL_OUTPUT_DIR}"
echo "[download-full] manifest=${manifest_file}"
echo "[download-full] output_dir=${FULL_OUTPUT_DIR}"

if [[ "${DOWNLOADER}" == "auto" ]]; then
  if command -v aria2c >/dev/null 2>&1; then
    DOWNLOADER="aria2c"
  elif command -v wget >/dev/null 2>&1; then
    DOWNLOADER="wget"
  else
    echo "ERROR: neither aria2c nor wget found in PATH." >&2
    exit 1
  fi
fi

case "${DOWNLOADER}" in
  aria2c)
    if [[ "${BY_CORPUS_SUBDIR}" == "1" ]]; then
      split_dir="$(mktemp -d)"
      python - "$manifest_file" "$split_dir" <<'PY'
import pathlib
import re
import sys
from urllib.parse import urlparse

manifest = pathlib.Path(sys.argv[1])
out_dir = pathlib.Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
handles = {}

def get_corpus(url: str) -> str:
    path = urlparse(url).path.strip("/")
    m = re.search(r"dolma-v[\w\.-]+/([^/]+)/", path)
    if m:
        return m.group(1)
    parts = path.split("/")
    return parts[-2] if len(parts) >= 2 else "misc"

for line in manifest.read_text().splitlines():
    url = line.strip()
    if not url or url.startswith("#"):
        continue
    corpus = get_corpus(url).replace("/", "_")
    fp = out_dir / f"{corpus}.txt"
    if corpus not in handles:
        handles[corpus] = fp.open("a")
    handles[corpus].write(url + "\n")

for h in handles.values():
    h.close()
PY
      for sub_manifest in "${split_dir}"/*.txt; do
        corpus="$(basename "${sub_manifest}" .txt)"
        corpus_dir="${FULL_OUTPUT_DIR}/${corpus}"
        mkdir -p "${corpus_dir}"
        echo "[download-full] corpus=${corpus} -> ${corpus_dir}"
        aria2c -x "${ARIA_CONNECTIONS}" -s "${ARIA_CONNECTIONS}" -c \
          -d "${corpus_dir}" -i "${sub_manifest}"
      done
      rm -rf "${split_dir}"
    else
      aria2c -x "${ARIA_CONNECTIONS}" -s "${ARIA_CONNECTIONS}" -c \
        -d "${FULL_OUTPUT_DIR}" -i "${manifest_file}"
    fi
    ;;
  wget)
    download_with_wget_parallel() {
      local manifest="$1"
      local out_dir="$2"
      mkdir -p "${out_dir}"
      # Run one wget per URL with bounded concurrency.
      grep -v '^[[:space:]]*$' "${manifest}" | grep -v '^[[:space:]]*#' | \
        xargs -P "${WGET_JOBS}" -I {} wget -c -P "${out_dir}" "{}"
    }
    if [[ "${BY_CORPUS_SUBDIR}" == "1" ]]; then
      split_dir="$(mktemp -d)"
      python - "$manifest_file" "$split_dir" <<'PY'
import pathlib
import re
import sys
from urllib.parse import urlparse

manifest = pathlib.Path(sys.argv[1])
out_dir = pathlib.Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
handles = {}

def get_corpus(url: str) -> str:
    path = urlparse(url).path.strip("/")
    m = re.search(r"dolma-v[\w\.-]+/([^/]+)/", path)
    if m:
        return m.group(1)
    parts = path.split("/")
    return parts[-2] if len(parts) >= 2 else "misc"

for line in manifest.read_text().splitlines():
    url = line.strip()
    if not url or url.startswith("#"):
        continue
    corpus = get_corpus(url).replace("/", "_")
    fp = out_dir / f"{corpus}.txt"
    if corpus not in handles:
        handles[corpus] = fp.open("a")
    handles[corpus].write(url + "\n")

for h in handles.values():
    h.close()
PY
      for sub_manifest in "${split_dir}"/*.txt; do
        corpus="$(basename "${sub_manifest}" .txt)"
        corpus_dir="${FULL_OUTPUT_DIR}/${corpus}"
        mkdir -p "${corpus_dir}"
        echo "[download-full] corpus=${corpus} -> ${corpus_dir} (wget_jobs=${WGET_JOBS})"
        download_with_wget_parallel "${sub_manifest}" "${corpus_dir}"
      done
      rm -rf "${split_dir}"
    else
      echo "[download-full] wget_jobs=${WGET_JOBS}"
      download_with_wget_parallel "${manifest_file}" "${FULL_OUTPUT_DIR}"
    fi
    ;;
  *)
    echo "ERROR: unsupported downloader '${DOWNLOADER}' (expected auto|aria2c|wget)." >&2
    exit 1
    ;;
esac

echo "[download] Done"
