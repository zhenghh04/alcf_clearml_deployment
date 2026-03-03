# Access Permission Control

This page defines a practical access model so other users cannot see or submit your jobs.

## 1) ClearML project visibility

Use a private project namespace and avoid shared default projects.

- Example private project: `private/hzheng`
- Put all personal tasks/pipelines under this project.

In ClearML Access Rules:

- Keep `ADMINS` with platform-wide access.
- Remove broad `USERS -> [All Projects]` access if possible.
- Add project-specific rule:
  - `Resource`: your private project
  - `Read & Modify`: your user (and optionally `ADMINS`)

If your deployment requires `USERS` global access, privacy cannot be guaranteed at project level.

## 2) Connector API access

The connector must not accept unauthenticated submits.

- Set `CONNECTOR_SHARED_SECRET` in `server/globus_auth/.env`
- Require header on submit:
  - `X-Connector-Key: <CONNECTOR_SHARED_SECRET>`

Example:

```bash
curl -sS -X POST "https://amscclearml.alcf.anl.gov/globus-connector/submit" \
  -H "Content-Type: application/json" \
  -H "X-Connector-Key: ${CONNECTOR_SHARED_SECRET}" \
  -d '{ ... }'
```

## 3) User-to-token mapping controls

Only the mapped ClearML user should be able to use stored Globus tokens.

- Current mapping key: `clearml_user_id`
- Link flow:
  - `GET /login?clearml_user_id=<id>&email=<email>`
  - `GET /callback` stores encrypted refresh token bundle

Recommended hardening:

- Set `STRICT_CLEARML_OWNER_CHECK=true`
- Configure ClearML service credentials in `.env`
- Validate that submit `clearml_task_id` owner matches `clearml_user_id`

## 4) Secret hygiene

Rotate and protect all secrets:

- `GLOBUS_CLIENT_SECRET`
- `CONNECTOR_SHARED_SECRET`
- `CONNECTOR_STATE_SECRET`
- `CONNECTOR_FERNET_KEY`

Store secrets in a secret manager (Vault/KMS) for production.

## 5) Audit and operations

- Keep connector logs (`journalctl` or file logs) and monitor failed submit attempts.
- Restrict connector network path with reverse-proxy ACLs/firewall.
- Use TLS-only public exposure.
