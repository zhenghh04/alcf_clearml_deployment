# Globus Endpoint Setup Helpers

This folder contains client-side connectivity helpers commonly used while configuring or accessing Globus-related services.

It also includes endpoint configuration references:
- `ENDPOINT_CONFIG_JSON.md`
- `compute.env.example`
- `transfer.env.example`

## SSH SOCKS proxy helper
```bash
bash clients/globus_endpoint_setup/ssh_proxy.sh
```

## SSH tunnel helper for ClearML/endpoint access
```bash
SSH_TUNNEL_TARGET=clearml bash clients/globus_endpoint_setup/ssh_tunnel_clearml.sh
```

Optional environment file:
- `clients/.env` (for values such as `SSH_TUNNEL_TARGET`)
