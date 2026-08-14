#!/bin/bash
# Partial-death-aware ClearML agent watchdog for Tara North.
# Tara has NO tmux and NO crontab, so relaunch is via `setsid nohup`. Healthy
# ONLY if BOTH a --services-mode daemon AND a non-services daemon are up (a dead
# services daemon with the login daemon alive is a partial death a bare pgrep
# would miss). launch_clearml_agent.sh sources tara/conda.sh, which exports the
# ALCF proxy — required or the relaunched agent's auth.login times out.
SYS="tara"
SETUP="$HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup"
_L=$(ps -eo args 2>/dev/null | grep "clearml-agent daemon" | grep -v grep)
printf '%s\n' "$_L" | grep -q -- "--services-mode" \
  && printf '%s\n' "$_L" | grep -v -- "--services-mode" | grep -q "clearml-agent daemon" \
  && exit 0
pkill -f "clearml-agent daemon" 2>/dev/null || true; sleep 2   # clear survivors -> clean relaunch
cd "$SETUP" || exit 1
CLIENT=${SYS} setsid nohup bash ./launch_clearml_agent.sh --run-daemons \
  >> "$HOME/clearml_watchdog_${SYS}.log" 2>&1 < /dev/null &
