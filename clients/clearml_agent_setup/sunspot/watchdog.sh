#!/bin/bash
SYS="sunspot"
SESSION="clearml-$SYS"
SETUP="$HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup"
_L=$(ps -eo args 2>/dev/null | grep "clearml-agent daemon" | grep -v grep)
printf '%s\n' "$_L" | grep -q -- "--services-mode" \
  && printf '%s\n' "$_L" | grep -v -- "--services-mode" | grep -q "clearml-agent daemon" \
  && exit 0
pkill -f "clearml-agent daemon" 2>/dev/null || true; sleep 2
cd "$SETUP" || exit 1
if command -v tmux >/dev/null 2>&1; then
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  tmux new-session -d -s "$SESSION" -x 220 -y 50 2>/dev/null \
    && tmux send-keys -t "$SESSION" "cd $SETUP && CLIENT=$SYS ./launch_clearml_agent.sh --run-daemons; exec bash" Enter \
    && exit 0
fi
CLIENT=$SYS setsid nohup bash ./launch_clearml_agent.sh --run-daemons >> ~/clearml_watchdog_$SYS.log 2>&1 < /dev/null &
