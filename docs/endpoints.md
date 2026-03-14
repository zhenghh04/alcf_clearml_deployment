# Endpoint Guide

## Discover endpoints

```bash
clearml-globus-endpoints --role any
clearml-globus-endpoints --role owner --json
```

## Configure endpoint templates

```bash
clearml-globus-configure-pbs-endpoint --endpoint-name my-pbs-endpoint
clearml-globus-configure-slurm-endpoint --endpoint-name my-slurm-endpoint
```

## Token helper

```bash
clearml-globus-token --type compute
clearml-globus-token --type transfer
```
