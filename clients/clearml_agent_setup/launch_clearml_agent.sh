#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT="${CLIENT:-sirius}"
QUEUE="${QUEUE:-$CLIENT}"
LOGIN_QUEUE="${LOGIN_QUEUE:-${QUEUE}-login}"
SERVICES_QUEUE="${SERVICES_QUEUE:-${QUEUE}-services}"
CLIENT_DIR="${SCRIPT_DIR}/${CLIENT}"
SYSTEM_CONF="${CLIENT_DIR}/system.conf"

export OPENBLAS_NUM_THREADS=1

if [[ ! -d "${CLIENT_DIR}" ]]; then
  echo "ERROR: client directory not found: ${CLIENT_DIR}" >&2
  exit 1
fi
if [[ ! -f "${CLIENT_DIR}/conda.sh" ]]; then
  echo "ERROR: missing conda setup script: ${CLIENT_DIR}/conda.sh" >&2
  exit 1
fi

# Scheduler resolution order:
# 1) explicit env var SCHEDULER
# 2) clients/clearml_agent_setup/<CLIENT>/system.conf (SCHEDULER=...)
# 3) fallback to pbs
if [[ -f "${SYSTEM_CONF}" ]]; then
  # Preserve explicit env override if provided by caller.
  SCHEDULER_ENV_OVERRIDE="${SCHEDULER:-}"
  # shellcheck disable=SC1090
  source "${SYSTEM_CONF}"
  SCHEDULER="${SCHEDULER_ENV_OVERRIDE:-${SCHEDULER:-}}"
fi
SCHEDULER="${SCHEDULER:-pbs}"   # one of: pbs, slurm

echo "Starting ClearML agent with client=${CLIENT} scheduler=${SCHEDULER}"
# shellcheck disable=SC1090
source "${CLIENT_DIR}/conda.sh"

export CLEARML_AGENT_SKIP_PIP_VENV_INSTALL="$(which python3)"
export CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1
export K8S_GLUE_POD_AGENT_INSTALL_ARGS="==2.0.7rc5"

template_candidates=(
  "${CLIENT_DIR}/${SCHEDULER}.template"
  "${SCRIPT_DIR}/${SCHEDULER}.template"
)

TEMPLATE_FILE=""
for candidate in "${template_candidates[@]}"; do
  if [[ -f "${candidate}" ]]; then
    TEMPLATE_FILE="${candidate}"
    break
  fi
done

if [[ -z "${TEMPLATE_FILE}" ]]; then
  echo "ERROR: no ${SCHEDULER}.template found under ${CLIENT_DIR} or ${SCRIPT_DIR}" >&2
  exit 1
fi

launcher_args=(--template-files "${TEMPLATE_FILE}" --queue "${QUEUE}")
case "${SCHEDULER}" in
  pbs)
    launcher_args+=(--use-pbs)
    ;;
  slurm)
    ;;
  *)
    echo "ERROR: unsupported SCHEDULER='${SCHEDULER}'. Use pbs or slurm." >&2
    exit 1
    ;;
esac

# Kill existing agents if present.
pkill clearml-agent-slurm || true
pkill clearml-agent || true

nohup clearml-agent-slurm "${launcher_args[@]}" &
nohup clearml-agent daemon --detached --queue "${LOGIN_QUEUE}" &
nohup clearml-agent daemon --detached --services-mode --queue "${SERVICES_QUEUE}" &

echo "Submitted daemon queues:"
echo "  scheduler queue: ${QUEUE}"
echo "  login queue:     ${LOGIN_QUEUE}"
echo "  services queue:  ${SERVICES_QUEUE}"
