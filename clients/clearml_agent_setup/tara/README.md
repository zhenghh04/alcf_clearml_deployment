# ClearML agent — Tara North (ALCF GH200, north-asn-01)

Reach: laptop cannot auth to Tara directly. Nodehop via the ALCF bastion:
`ssh bastion 'ssh north-asn-01.head.north.tara.alcf.anl.gov "<cmd>"'`.

Tara specifics (differ from every other client):
- **No conda / no tmux / no crontab.** Agent runs in a py3.11 venv
  (`tara/envs/clearml`, built from `/usr/bin/python3.11`). Persistence is a
  `setsid nohup` self-looping watchdog (`tara/watchdog-loop.sh`), not tmux/cron.
- **Proxy-only egress.** `tara/conda.sh` exports `http(s)_proxy=http://proxy.alcf.anl.gov:3128`
  (http scheme). Without it the agent's auth.login times out and it exits.
- **Reboots often** (pre-production) — nothing here survives a reboot; restart manually.

## Build the venv + install (run on north-asn-01, proxy exported)
```bash
export https_proxy=http://proxy.alcf.anl.gov:3128 http_proxy=http://proxy.alcf.anl.gov:3128
SETUP=$HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup
/usr/bin/python3.11 -m venv "$SETUP/tara/envs/clearml"
source "$SETUP/tara/envs/clearml/bin/activate"
python3 -m pip install -U pip
bash "$SETUP/install_clearml.sh"     # sources clients/.env for the allegro index
```

## Launch (detached; no tmux)
```bash
cd $HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup
CLIENT=tara setsid nohup bash ./launch_clearml_agent.sh --run-daemons \
  >> $HOME/clearml_tara_agent.log 2>&1 < /dev/null &
# then the watchdog loop:
setsid nohup bash tara/watchdog-loop.sh >> $HOME/clearml_watchdog_tara_loop.log 2>&1 < /dev/null &
```

Serves three queues: `tara` (PBS compute dispatch — account/queue in `tara/pbs.template`
still UNVERIFIED), `tara-services` (login-node shell tasks), `tara-login`.
