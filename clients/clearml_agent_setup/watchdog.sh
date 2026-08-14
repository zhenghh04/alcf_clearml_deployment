#!/bin/bash
# Generic partial-death-aware ClearML agent watchdog, keyed on CLIENT -- the
# same contract as launch_clearml_agent.sh, so the two never diverge.
#
# ALCF/DOE login nodes have no reliable crond/tmux, so nothing re-runs the agent
# on its own. Persistence is driven externally by an ALCF GitLab-CI *pipeline
# schedule* (the missing crond): it invokes this single-shot script every
# ~20 min on a login node, as the triggering user, via the Jacamar shell
# executor. Relaunch is via `setsid nohup` so the daemon outlives the CI job.
#
# The expected daemon set is derived the SAME way launch_clearml_agent.sh starts
# them, so a 3-daemon watchdog can never land on a 2-daemon system and
# thrash-relaunch every tick. From <CLIENT>/system.conf:
#   SCHEDULER=services             -> services-mode daemon only
#   SCHEDULER=pbs|slurm (default)  -> login + services + compute launcher
#   WATCHDOG_COMPUTE=0             -> drop the compute launcher even under
#                                     pbs/slurm (e.g. Tara, where
#                                     clearml-agent-slurm needs a private build
#                                     and does not stay up -> otherwise thrash)
#
# Healthy ONLY if every expected daemon is up; a dead services/compute daemon
# with the login daemon still alive is a partial death a bare `pgrep
# clearml-agent` would miss. On any miss: clear survivors and cleanly relaunch
# the whole stack via launch_clearml_agent.sh, which sources <CLIENT>/conda.sh
# (ALCF proxy + venv) -- required or the relaunched agent's auth.login times out.
#
# Usage:  CLIENT=<system> bash watchdog.sh     (or)     bash watchdog.sh <system>
set +x

SYS="${CLIENT:-${1:-}}"
if [[ -z "${SYS}" ]]; then
  echo "ERROR: set CLIENT=<system> (or pass it as \$1)" >&2
  exit 2
fi
SETUP="${SETUP_DIR:-$HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup}"
CONF="${SETUP}/${SYS}/system.conf"

SCHEDULER="pbs"
WATCHDOG_COMPUTE=1
# shellcheck disable=SC1090
[[ -f "${CONF}" ]] && source "${CONF}"
SCHEDULER="${SCHEDULER:-pbs}"
WATCHDOG_COMPUTE="${WATCHDOG_COMPUTE:-1}"

want_login=1; want_services=1; want_compute="${WATCHDOG_COMPUTE}"
if [[ "${SCHEDULER}" == "services" ]]; then
  want_login=0
  want_compute=0
fi

_L=$(ps -eo args 2>/dev/null | grep -E "clearml-agent" | grep -v grep)
have_services=$(printf '%s\n' "$_L" | grep -- "clearml-agent daemon" | grep -q -- "--services-mode" && echo 1)
have_login=$(printf '%s\n' "$_L" | grep -- "clearml-agent daemon" | grep -v -- "--services-mode" | grep -q "clearml-agent daemon" && echo 1)
have_compute=$(printf '%s\n' "$_L" | grep -q "clearml-agent-slurm" && echo 1)

ok=1
[[ "${want_login}"    == 1 && -z "${have_login}"    ]] && ok=0
[[ "${want_services}" == 1 && -z "${have_services}" ]] && ok=0
[[ "${want_compute}"  == 1 && -z "${have_compute}"  ]] && ok=0
if [[ "${ok}" == 1 ]]; then
  exit 0
fi

# Any expected daemon missing -> clear survivors for a clean, single relaunch.
pkill -f "clearml-agent daemon" 2>/dev/null || true
pkill -f "clearml-agent-slurm" 2>/dev/null || true
sleep 2
cd "${SETUP}" || exit 1
CLIENT="${SYS}" setsid nohup bash ./launch_clearml_agent.sh --run-daemons \
  >> "$HOME/clearml_watchdog_${SYS}.log" 2>&1 < /dev/null &
