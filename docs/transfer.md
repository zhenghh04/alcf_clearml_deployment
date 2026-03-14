# Transfer Guide

Use `clearml-globus-transfer` for direct transfer and `clearml-globus-transfer-launch` for queued ClearML tasks.

## Minimal flow

1. Export transfer token: `eval "$(clearml-globus-token --type transfer)"`
2. Submit transfer with source/destination endpoint and paths.
3. Optionally enqueue a transfer task to a queue.

## Notes

- Prefer UUIDs if alias resolution is ambiguous.
- A `403 PermissionDenied` usually indicates endpoint identity/domain policy mismatch.
