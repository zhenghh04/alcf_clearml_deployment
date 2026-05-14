# Cerebras ClearML agent setup

One `clearml-agent` daemon runs in `--services-mode` on a Cerebras user
node (`cer-usn-01`, with `cer-usn-02` as manual hot spare). Tasks
enqueued to **`cerebras-services`** are picked up by the daemon, which
sources `~/R_2.9.0/venv_cerebras_pt/bin/activate` and executes the
task's `run.sh`. The script in turn runs `python train.py …`, which
ships the workload to the CS-3 appliance via Cerebras `run_utils` →
`csctl`.

There is **no** PBS/Slurm scheduler glue and **no** `cerebras-login`
queue — the user node is the entry point.

## One-time bootstrap on `cer-usn-01`

```bash
ssh cerebras.alcf.anl.gov
ssh cer-usn-01

# Cerebras venv (per https://docs.alcf.anl.gov/ai-testbed/cerebras/customizing-environment/)
mkdir -p ~/R_2.9.0
cd ~/R_2.9.0
/usr/bin/python3.11 -m venv venv_cerebras_pt
source venv_cerebras_pt/bin/activate
pip install --upgrade pip

# ClearML client + agent (proxy needed for PyPI; provided by conda.sh later)
export https_proxy=http://proxy.alcf.anl.gov:3128
pip install clearml clearml-agent

# ClearML config: copy ~/clearml.conf from amscclearml.alcf.anl.gov UI
#   (Settings → "ClearML Conf" → download)
# Place at ~/clearml.conf
```

## Start the daemon (in tmux)

```bash
git clone <this repo path or symlink it> ~/clearml-agent-setup
cd ~/clearml-agent-setup/clients/clearml_agent_setup

tmux new -s clearml-agent-cerebras
CLIENT=cerebras ./launch_clearml_agent.sh --run-daemons
# Ctrl-b d to detach
```

Inspect:

```bash
tmux attach -t clearml-agent-cerebras
# look for "Worker registered, queue=cerebras-services"
```

## Stop / restart

```bash
CLIENT=cerebras ./launch_clearml_agent.sh --stop-daemons
CLIENT=cerebras ./launch_clearml_agent.sh --run-daemons
```

## Hot spare on `cer-usn-02`

Same bootstrap, same `tmux` session name. Two daemons on the same
queue is supported by ClearML — whichever picks up the task first wins.
This survives a reboot of one user node.

## Smoke test

After the daemon is running, enqueue
`agentic_workflows/jobs/cerebras/clearml_smoke/run.sh` to the
`cerebras-services` queue (project `AmSC-Smoke`). It should print
`csctl get cluster` output and `cerebras_appliance OK`.
