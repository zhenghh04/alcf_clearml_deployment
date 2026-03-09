# Troubleshooting

## `Token is not active`

- Re-export a fresh token with `clearml-globus-token --type <compute|transfer> --login-if-needed`.
- Confirm env var is non-empty (`echo ${#VAR}`).

## `PermissionDenied` on transfer endpoint login

- Endpoint policy may require specific identity domain (for example `alcf.anl.gov`).
- Re-login with correct identity and consent.

## Duplicate endpoint alias matches

- Pass endpoint UUIDs directly to avoid alias ambiguity.

## ClearML `Task` has no `set_environment`

- Use `task.set_parameters_as_dict({"env:KEY": "value"})` (already applied in bridge code).
