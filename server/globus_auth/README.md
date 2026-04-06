# Globus Connector (token broker)

This service implements delegated Globus Compute submission on behalf of a ClearML user.

Access control guidance:
- `server/globus_auth/ACCESS_PERMISSION_CONTROL.md`

Globus auth setup guide:
- `server/globus_auth/ENABLE_GLOBUS_AUTH.md`

## Endpoints

- `GET /login?clearml_user_id=<id>&email=<email>`
  - Starts OAuth flow at Globus.
- `GET /callback?code=...&state=...`
  - Exchanges auth code, stores encrypted refresh token bundle.
- `POST /submit`
  - Refreshes user access token and submits a Globus Compute task.

## 1) Configure your Globus app (App 2)

Use a `Confidential Client` app for this connector and register:

- Redirect URI: `http://localhost:8503/callback` (local dev)
- Scopes:
  - `openid`
  - `profile`
  - `email`
  - `https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all`

## 2) Environment setup

```bash
cp server/globus_auth/.env.example server/globus_auth/.env
```

Generate encryption key:

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

Put that value into `CONNECTOR_FERNET_KEY`.

## 3) Install and run

```bash
pip install -r server/globus_auth/requirements.txt
set -a; source server/globus_auth/.env; set +a
uvicorn server.globus_auth.main:app --host 0.0.0.0 --port 8503
```

Or use the launcher:

```bash
server/globus_auth/launch_connector.sh
```

Useful options:

```bash
INSTALL_DEPS=1 PORT=8503 server/globus_auth/launch_connector.sh
DETACH=1 LOG_FILE=server/globus_auth/connector.log server/globus_auth/launch_connector.sh
```

## 3b) Run as a systemd service

Install as a user service (no sudo):

```bash
server/globus_auth/install_systemd_service.sh
```

Install as a system service:

```bash
server/globus_auth/install_systemd_service.sh --system
```

Service control:

```bash
systemctl --user status globus-connector.service
systemctl --user restart globus-connector.service
journalctl --user -u globus-connector.service -f
```

## 4) Bootstrap user token

Use your ClearML user id and email (from ClearML profile/API).

Open in browser:

```bash
http://localhost:8503/login?clearml_user_id=<CLEARML_USER_ID>&email=<EMAIL>
```

After consent, callback stores encrypted token in SQLite (`CONNECTOR_DB_PATH`).

## 5) Submit on behalf of user

```bash
curl -sS -X POST "http://localhost:8503/submit" \
  -H "Content-Type: application/json" \
  -H "X-Connector-Key: ${CONNECTOR_SHARED_SECRET}" \
  -d '{
    "clearml_user_id": "<CLEARML_USER_ID>",
    "email": "<EMAIL>",
    "endpoint_id": "<GLOBUS_ENDPOINT_ID>",
    "input_value": 7,
    "timeout_sec": 1200
  }'
```

Expected response includes `globus_task_id` and `result`.

## Production hardening checklist

- Put connector behind HTTPS and reverse proxy.
- Move token storage from local SQLite to managed DB.
- Use KMS/Vault envelope encryption for token payload.
- Replace shared header key with signed service JWTs.
- Enable and validate `STRICT_CLEARML_OWNER_CHECK` with known owner field in your ClearML deployment.
