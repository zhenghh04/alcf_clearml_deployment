# Data movement tests

This folder contains a local task to move data between ALCF Globus endpoints. The transfer runs on the local machine using Globus CLI and logs status to ClearML if available.

## Prereqs
- Globus CLI installed and authenticated (`globus login`)
    ```bash
    pip install globus-cli
    ```
- ClearML configured (optional)

## Run
Set source/destination endpoints and paths via arguments (env vars are accepted as defaults). Endpoint names like `alcf#dtn_eagle` will be resolved automatically using `globus endpoint search` on this CLI version:
```bash
python tests/data_movement/transfer_globus.py \
  --src-endpoint alcf#dtn_eagle \
  --dst-endpoint alcf#dtn_flare \
  --src-path xxx \
  --dst-path xxx \
  --recursive \
  --poll-interval 10
```

Optional:
- `GLOBUS_LABEL` custom transfer label
- `GLOBUS_SYNC_LEVEL` (e.g., `mtime`, `checksum`, `exists`)
- `GLOBUS_DRY_RUN=1` to print the command without executing
- `GLOBUS_POLL_INTERVAL` polling interval in seconds for ClearML progress logging
- `--no-wait` to return immediately after submitting the transfer

## Enqueue via ClearML
Use `launch_transfer.py` to create and enqueue a ClearML task:
```bash
python tests/data_movement/launch_transfer.py \
  --src-endpoint alcf#dtn_eagle \
  --dst-endpoint alcf#dtn_flare \
  --src-path /datasets/test.txt \
  --dst-path /datascience/test.txt \
  --queue sirius-login
```
