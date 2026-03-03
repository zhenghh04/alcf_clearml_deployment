#!/usr/bin/env bash
set -euo pipefail

MODE="user"
if [[ "${1:-}" == "--system" ]]; then
  MODE="system"
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE="${ROOT_DIR}/server/globus_auth/systemd/globus-connector.service.template"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
RUN_USER="${RUN_USER:-$(id -un)}"

if [[ ! -f "${TEMPLATE}" ]]; then
  echo "ERROR: missing template: ${TEMPLATE}" >&2
  exit 1
fi

rendered="$(mktemp)"
sed \
  -e "s|@ROOT_DIR@|${ROOT_DIR}|g" \
  -e "s|@PYTHON_BIN@|${PYTHON_BIN}|g" \
  -e "s|@RUN_USER@|${RUN_USER}|g" \
  "${TEMPLATE}" > "${rendered}"

if [[ "${MODE}" == "user" ]]; then
  target_dir="${HOME}/.config/systemd/user"
  mkdir -p "${target_dir}"
  cp "${rendered}" "${target_dir}/globus-connector.service"
  systemctl --user daemon-reload
  systemctl --user enable --now globus-connector.service
  echo "Installed user service: ${target_dir}/globus-connector.service"
  echo "Check status: systemctl --user status globus-connector.service"
else
  sudo cp "${rendered}" /etc/systemd/system/globus-connector.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now globus-connector.service
  echo "Installed system service: /etc/systemd/system/globus-connector.service"
  echo "Check status: sudo systemctl status globus-connector.service"
fi

rm -f "${rendered}"
