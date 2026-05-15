# g3plus client

Services-mode ClearML agent on a personal home host
(`g3plus`, Intel N150 mini-PC, Ubuntu 25.10).

## Why services-mode?

Plain Linux PC, no PBS/Slurm. One `clearml-agent daemon --services-mode`
handles all `g3plus-services` queue work. This host is a ClearML
services-mode worker, local dev/build machine, and future Globus
data-staging endpoint.

## ClearML server

**Not** `amscclearml.alcf.anl.gov` (ALCF-internal DNS; unreachable from
outside ALCF). This agent talks to the personal ClearML instance at:

- API:   `https://api.clearml.lionlambstone.org`
- Web:   `https://app.clearml.lionlambstone.org`
- Files: `https://files.clearml.lionlambstone.org`

The `~/clearml.conf` on g3plus must point to these URLs.

## Bootstrap (one-time)

```bash
# 1. Clone the deployment repo (use SSH; HTTPS to github.com is firewalled)
mkdir -p ~/clearml && cd ~/clearml
git clone git@github.com:zhenghh04/alcf_clearml_deployment.git

# 2. Create venv (g3plus has /opt/miniconda3 but we isolate the agent)
python3 -m venv ~/clearml/venv
~/clearml/venv/bin/python -m pip install -U pip

# 3. Install clearml-agent (credentials come from .env)
source ~/clearml/alcf_clearml_deployment/.env
~/clearml/venv/bin/python -m pip install \
    --extra-index-url "https://${CLEARML_PIP_PACKAGE_USER}:${CLEARML_PIP_PACKAGE_PASS}@packages.allegro.ai/repository/clearml_agent_slurm/simple" \
    clearml-agent==2.0.7rc5

# 4. Ensure ~/clearml.conf points to api.clearml.lionlambstone.org
#    (not amscclearml.alcf.anl.gov) and has lionlambstone credentials.
```

## Launch

```bash
cd ~/clearml/alcf_clearml_deployment/clients/clearml_agent_setup
CLIENT=g3plus bash launch_clearml_agent.sh --run-daemons
```

`launch_clearml_agent.sh` reads `g3plus/system.conf` (`SCHEDULER=services`),
sources `g3plus/conda.sh` (activates the venv), and starts a single
`--services-mode` daemon on the `g3plus-services` queue.

## Pre-flight: queue must exist on the ClearML server

Create `g3plus-services` in the lionlambstone WebUI
(Settings → Queues → +Queue) OR via the SDK before launching:

```python
from clearml.backend_api.session.client import APIClient
c = APIClient()
qid = c.queues.create(name="g3plus-services").id
print("g3plus-services ->", qid)
```
