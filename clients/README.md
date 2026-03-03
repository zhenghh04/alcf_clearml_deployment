# Clients Setup

Currently, there are two ways to run jobs from the client side:

1. Through ClearML agents
- `clearml-agent` (login/services queues)
- `clearml-agent-slurm` (scheduler-backed queue submission)
- Setup/docs: [clients/clearml_agent_setup/README.md](clearml_agent_setup/README.md)

2. Through Globus Compute
- Endpoint-driven remote execution via the Globus bridge workflow.
- Setup helpers/docs: [clients/globus_endpoint_setup/README.md](globus_endpoint_setup/README.md)

The `clients/` directory is split into two setup tracks:

1. `clients/clearml_agent_setup/`
- ClearML agent installation scripts
- Queue launch scripts
- Machine-specific scheduler templates/configs

2. `clients/globus_endpoint_setup/`
- SSH proxy helper
- SSH tunnel helper for endpoint/service access

Read:
- [clients/clearml_agent_setup/README.md](clearml_agent_setup/README.md)
- [clients/globus_endpoint_setup/README.md](globus_endpoint_setup/README.md)
