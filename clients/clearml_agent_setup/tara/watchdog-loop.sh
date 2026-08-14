#!/bin/bash
# Crond-independent watchdog loop for Tara North (no crontab, no tmux).
# Launch detached ONCE with:
#   cd $HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup
#   setsid nohup bash tara/watchdog-loop.sh >> $HOME/clearml_watchdog_tara_loop.log 2>&1 < /dev/null &
# Survives SSH disconnect (setsid detaches from the session) but NOT a node
# reboot — Tara is pre-production and reboots often, so post-reboot needs a
# manual restart.
SETUP="$HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup"
while true; do
  bash "$SETUP/tara/watchdog.sh"
  sleep 300
done
