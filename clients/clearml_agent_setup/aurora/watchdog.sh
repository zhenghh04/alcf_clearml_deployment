#!/bin/bash
# Partial-death-aware ClearML agent watchdog for Aurora.
# Aurora login nodes have NO crond and NO tmux; persistence is driven externally
# by an ALCF GitLab-CI *pipeline schedule* (the missing crond) that invokes this
# single-shot script every ~20 min. Relaunch is via `setsid nohup`.
#
# Aurora runs THREE daemons off launch_clearml_agent.sh --run-daemons:
#   1. login    : clearml-agent daemon --queue aurora-login
#   2. services : clearml-agent daemon --services-mode --queue aurora-services
#   3. compute  : clearml-agent-slurm --template-files ... --queue aurora --use-pbs
# Healthy ONLY if all three are up. A dead services or compute daemon with the
# login daemon still alive is a partial death a bare `pgrep clearml-agent` would
# miss. launch_clearml_agent.sh sources aurora/conda.sh, which exports the ALCF
# proxy + activates the frameworks venv -- required or the relaunched agent's
# auth.login times out.
SYS="aurora"
SETUP="$HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup"

_L=$(ps -eo args 2>/dev/null | grep -E "clearml-agent" | grep -v grep)
have_services=$(printf '%s\n' "$_L" | grep -- "clearml-agent daemon" | grep -q -- "--services-mode" && echo 1)
have_login=$(printf '%s\n' "$_L" | grep -- "clearml-agent daemon" | grep -v -- "--services-mode" | grep -q "clearml-agent daemon" && echo 1)
have_compute=$(printf '%s\n' "$_L" | grep -q "clearml-agent-slurm" && echo 1)

if [[ -n "$have_services" && -n "$have_login" && -n "$have_compute" ]]; then
  exit 0
fi

# Any daemon missing -> clear survivors for a clean, single relaunch of all three.
pkill -f "clearml-agent daemon" 2>/dev/null || true
pkill -f "clearml-agent-slurm" 2>/dev/null || true
sleep 2
cd "$SETUP" || exit 1
CLIENT=${SYS} setsid nohup bash ./launch_clearml_agent.sh --run-daemons \
  >> "$HOME/clearml_watchdog_${SYS}.log" 2>&1 < /dev/null &
