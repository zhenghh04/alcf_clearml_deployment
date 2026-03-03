# Enable Globus Auth (Step-by-Step)

This guide enables:

- ClearML login via Globus (SSO)
- Connector delegated submission to Globus Compute

Use two separate Globus apps.

## App 1: ClearML SSO app

Create a Globus `Confidential Client` for ClearML login.

Set in Globus app:

- Redirect URI: `https://amscclearml.alcf.anl.gov/callback_<clearml_generated_id>`
  - Use the exact callback URI shown in ClearML IdP settings.
- Scopes for login: `openid`, `profile`, `email`

In ClearML IdP config:

- Authorization endpoint: `https://auth.globus.org/v2/oauth2/authorize`
- Access token endpoint: `https://auth.globus.org/v2/oauth2/token`
- Userinfo endpoint: `https://auth.globus.org/v2/oauth2/userinfo`
- Revocation endpoint: `https://auth.globus.org/v2/oauth2/token/revoke` (or leave empty)
- Code challenge method: `None`
- Standard scopes: `openid,profile,email`
- Claims mapping:
  - user id: `sub`
  - email: `email`
  - name: `preferred_username` (or `name`)

Verify with ClearML `Test provider connection` before using login button.

## App 2: Connector app (token broker)

Create another Globus `Confidential Client` for connector OAuth flow.

Set in Globus app:

- Redirect URI (proxy path mode):
  - `https://amscclearml.alcf.anl.gov/globus-connector/callback`
- Scopes:
  - `openid`
  - `profile`
  - `email`
  - `https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all`

## Connector configuration

Update `server/globus_auth/.env`:

```env
GLOBUS_CLIENT_ID=<app2_client_id>
GLOBUS_CLIENT_SECRET=<app2_client_secret>
GLOBUS_REDIRECT_URI=https://amscclearml.alcf.anl.gov/globus-connector/callback
GLOBUS_SCOPES=openid,profile,email,https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all
CONNECTOR_BASE_URL=https://amscclearml.alcf.anl.gov/globus-connector
```

Generate secrets:

```bash
python - <<'PY'
import secrets
from cryptography.fernet import Fernet
print("CONNECTOR_STATE_SECRET=", secrets.token_urlsafe(64))
print("CONNECTOR_SHARED_SECRET=", secrets.token_urlsafe(48))
print("CONNECTOR_FERNET_KEY=", Fernet.generate_key().decode())
PY
```

## Reverse proxy routing

Route connector path to backend service (example backend port `8503`):

```nginx
location ^~ /globus-connector/ {
    proxy_pass http://127.0.0.1:8503/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-Prefix /globus-connector;
}
```

## Run connector

```bash
server/globus_auth/launch_connector.sh
```

or as systemd:

```bash
server/globus_auth/install_systemd_service.sh
```

## Validate flow

1. Health check:

```bash
curl -sS https://amscclearml.alcf.anl.gov/globus-connector/health
```

2. Link user token:

```text
https://amscclearml.alcf.anl.gov/globus-connector/login?clearml_user_id=<CLEARML_USER_ID>&email=<EMAIL>
```

Expected callback response:

```json
{"status":"ok","message":"Globus tokens stored for user",...}
```

3. Submit delegated job:

```bash
curl -sS -X POST "https://amscclearml.alcf.anl.gov/globus-connector/submit" \
  -H "Content-Type: application/json" \
  -H "X-Connector-Key: ${CONNECTOR_SHARED_SECRET}" \
  -d '{
    "clearml_user_id":"<CLEARML_USER_ID>",
    "email":"<EMAIL>",
    "endpoint_id":"<GLOBUS_ENDPOINT_ID>",
    "input_value":7,
    "timeout_sec":1200
  }'
```

## Common failures

- `Mismatching redirect URI`
  - App redirect and `GLOBUS_REDIRECT_URI` are not identical.
- `Invalid connector key`
  - wrong `X-Connector-Key` header value.
- ClearML SSO fails but connector works
  - App 1 and App 2 credentials are mixed.
