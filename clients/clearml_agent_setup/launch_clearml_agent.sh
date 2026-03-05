#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT="${CLIENT:-sirius}"
QUEUE="${QUEUE:-$CLIENT}"
LOGIN_QUEUE="${LOGIN_QUEUE:-${QUEUE}-login}"
SERVICES_QUEUE="${SERVICES_QUEUE:-${QUEUE}-services}"
CLIENT_DIR="${SCRIPT_DIR}/${CLIENT}"
SYSTEM_CONF="${CLIENT_DIR}/system.conf"
SERVICE_NAME="clearml-agent-${CLIENT}.service"
USER_SERVICE_DIR="${HOME}/.config/systemd/user"
USER_SERVICE_PATH="${USER_SERVICE_DIR}/${SERVICE_NAME}"
SYSTEM_SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

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
  SCHEDULER_ENV_OVERRIDE="${SCHEDULER:-}"
  # shellcheck disable=SC1090
  source "${SYSTEM_CONF}"
  SCHEDULER="${SCHEDULER_ENV_OVERRIDE:-${SCHEDULER:-}}"
fi
SCHEDULER="${SCHEDULER:-pbs}"   # one of: pbs, slurm

stop_daemons() {
  pkill clearml-agent-slurm || true
  pkill clearml-agent || true
}

run_daemons() {
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

  stop_daemons
  nohup clearml-agent-slurm "${launcher_args[@]}" &
  nohup clearml-agent daemon --detached --queue "${LOGIN_QUEUE}" &
  nohup clearml-agent daemon --detached --services-mode --queue "${SERVICES_QUEUE}" &

  echo "Submitted daemon queues:"
  echo "  scheduler queue: ${QUEUE}"
  echo "  login queue:     ${LOGIN_QUEUE}"
  echo "  services queue:  ${SERVICES_QUEUE}"
}

write_service_unit() {
  local target="${1}"
  local wanted_by="${2}"
  mkdir -p "$(dirname "${target}")"
  cat > "${target}" <<UNIT
[Unit]
Description=ClearML agent daemons for client ${CLIENT}
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${SCRIPT_DIR}
Environment=CLIENT=${CLIENT}
ExecStart=${SCRIPT_DIR}/launch_clearml_agent.sh --run-daemons
ExecStop=${SCRIPT_DIR}/launch_clearml_agent.sh --stop-daemons

[Install]
WantedBy=${wanted_by}
UNIT
}

install_user_service() {
  command -v systemctl >/dev/null
  if ! systemctl --user show-environment >/dev/null 2>&1; then
    echo "ERROR: user systemd bus is unavailable in this session." >&2
    echo "Try one of the following:" >&2
    echo "  1) Use system-level service: $0 --install-system" >&2
    echo "  2) Enable lingering and re-login, then retry --install-service:" >&2
    echo "     sudo loginctl enable-linger ${USER}" >&2
    exit 1
  fi
  write_service_unit "${USER_SERVICE_PATH}" "default.target"
  systemctl --user daemon-reload
  systemctl --user enable --now "${SERVICE_NAME}"
  echo "Installed user service: ${USER_SERVICE_PATH}"
  systemctl --user status "${SERVICE_NAME}" --no-pager || true
}

install_system_service() {
  command -v systemctl >/dev/null
  local tmp_unit
  tmp_unit="$(mktemp)"
  write_service_unit "${tmp_unit}" "multi-user.target"
  sudo install -m 0644 "${tmp_unit}" "${SYSTEM_SERVICE_PATH}"
  rm -f "${tmp_unit}"
  sudo systemctl daemon-reload
  sudo systemctl enable --now "${SERVICE_NAME}"
  echo "Installed system service: ${SYSTEM_SERVICE_PATH}"
  sudo systemctl status "${SERVICE_NAME}" --no-pager || true
}

uninstall_user_service() {
  systemctl --user disable --now "${SERVICE_NAME}" >/dev/null 2>&1 || true
  rm -f "${USER_SERVICE_PATH}"
  systemctl --user daemon-reload
}

uninstall_system_service() {
  sudo systemctl disable --now "${SERVICE_NAME}" >/dev/null 2>&1 || true
  sudo rm -f "${SYSTEM_SERVICE_PATH}"
  sudo systemctl daemon-reload
}

usage() {
  cat <<USAGE
Usage: $0 [command]

Commands:
  --run-daemons         Start ClearML daemons (default behavior)
  --stop-daemons        Stop ClearML daemons
  --install-service     Install as a user-level systemd service and start it
  --install-system      Install as a system-level systemd service and start it
  --start-service       Start installed user service
  --stop-service        Stop installed user service
  --status-service      Show status of installed user service
  --uninstall-service   Remove installed user service
  --uninstall-system    Remove installed system service
  --help                Show this help
USAGE
}

cmd="${1:---run-daemons}"
case "${cmd}" in
  --run-daemons)
    run_daemons
    ;;
  --stop-daemons)
    stop_daemons
    ;;
  --install-service)
    install_user_service
    ;;
  --install-system)
    install_system_service
    ;;
  --start-service)
    systemctl --user start "${SERVICE_NAME}"
    ;;
  --stop-service)
    systemctl --user stop "${SERVICE_NAME}"
    ;;
  --status-service)
    systemctl --user status "${SERVICE_NAME}" --no-pager
    ;;
  --uninstall-service)
    uninstall_user_service
    ;;
  --uninstall-system)
    uninstall_system_service
    ;;
  --help|-h)
    usage
    ;;
  *)
    echo "ERROR: unknown command ${cmd}" >&2
    usage
    exit 1
    ;;
esac
