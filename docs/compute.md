# Compute Guide

Use `clearml-globus-submit` for Globus Compute-backed execution.

## Minimal flow

1. Configure endpoint templates with `clearml-globus-configure-pbs-endpoint` or `clearml-globus-configure-slurm-endpoint`.
2. Start endpoint and confirm it is online.
3. Submit a bridge task via `clearml-globus-submit`.

## Auth

- Compute token export: `eval "$(clearml-globus-token --type compute)"`
- Endpoint listing: `clearml-globus-endpoints --role any`
