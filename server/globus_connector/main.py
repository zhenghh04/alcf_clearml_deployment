import os
import operator
from dataclasses import dataclass
from typing import Any, Dict, Optional

import globus_sdk
from clearml import Task
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from globus_compute_sdk import Client as ComputeClient
from globus_compute_sdk import Executor
from itsdangerous import URLSafeSerializer
from pydantic import BaseModel, Field

try:
    from .token_store import TokenStore
except ImportError:  # Allows running as a script from this directory.
    from token_store import TokenStore


@dataclass
class Settings:
    globus_client_id: str
    globus_client_secret: str
    globus_redirect_uri: str
    globus_scopes: list[str]
    connector_state_secret: str
    connector_db_path: str
    connector_fernet_key: str
    connector_base_url: str
    connector_shared_secret: str
    strict_clearml_owner_check: bool


class SubmitRequest(BaseModel):
    clearml_user_id: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    endpoint_id: str = Field(..., min_length=1)
    input_value: int = 7
    timeout_sec: int = 1800
    clearml_task_id: Optional[str] = None


def load_settings() -> Settings:
    scopes = os.getenv("GLOBUS_SCOPES", "openid,profile,email").split(",")
    scopes = [s.strip() for s in scopes if s.strip()]

    required = [
        "GLOBUS_CLIENT_ID",
        "GLOBUS_CLIENT_SECRET",
        "GLOBUS_REDIRECT_URI",
        "CONNECTOR_STATE_SECRET",
        "CONNECTOR_FERNET_KEY",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    return Settings(
        globus_client_id=os.environ["GLOBUS_CLIENT_ID"],
        globus_client_secret=os.environ["GLOBUS_CLIENT_SECRET"],
        globus_redirect_uri=os.environ["GLOBUS_REDIRECT_URI"],
        globus_scopes=scopes,
        connector_state_secret=os.environ["CONNECTOR_STATE_SECRET"],
        connector_db_path=os.getenv("CONNECTOR_DB_PATH", "server/globus_connector/tokens.db"),
        connector_fernet_key=os.environ["CONNECTOR_FERNET_KEY"],
        connector_base_url=os.getenv("CONNECTOR_BASE_URL", "http://localhost:8000"),
        connector_shared_secret=os.getenv("CONNECTOR_SHARED_SECRET", ""),
        strict_clearml_owner_check=os.getenv("STRICT_CLEARML_OWNER_CHECK", "false").lower()
        == "true",
    )


settings = load_settings()
state_signer = URLSafeSerializer(settings.connector_state_secret, salt="globus-connector-state")
token_store = TokenStore(settings.connector_db_path, settings.connector_fernet_key)
app = FastAPI(title="Globus Connector", version="0.1.0")


def _make_auth_client() -> globus_sdk.ConfidentialAppAuthClient:
    return globus_sdk.ConfidentialAppAuthClient(
        settings.globus_client_id,
        settings.globus_client_secret,
    )


def _validate_submit_secret(x_connector_key: Optional[str]) -> None:
    if not settings.connector_shared_secret:
        return
    if x_connector_key != settings.connector_shared_secret:
        raise HTTPException(status_code=401, detail="Invalid connector key")


def _maybe_validate_task_owner(clearml_task_id: str, clearml_user_id: str) -> None:
    if not settings.strict_clearml_owner_check:
        return

    task = Task.get_task(task_id=clearml_task_id)
    owner_candidates = [
        getattr(task, "user", None),
        getattr(getattr(task, "data", None), "user", None),
    ]
    owners = [str(x) for x in owner_candidates if x is not None]
    if not owners:
        raise HTTPException(
            status_code=400,
            detail="Cannot resolve task owner from ClearML task object for strict check",
        )
    if clearml_user_id not in owners:
        raise HTTPException(
            status_code=403,
            detail="clearml_user_id does not match task owner for strict check",
        )


def _extract_funcx_tokens(token_response: globus_sdk.OAuthTokenResponse) -> Dict[str, Any]:
    by_rs = token_response.by_resource_server
    if "funcx_service" not in by_rs:
        raise HTTPException(
            status_code=400,
            detail="Token response missing funcx_service scope; check connector app scopes.",
        )
    return by_rs


def _refresh_access_token(token_bundle: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    funcx = token_bundle.get("funcx_service", {})
    refresh_token = funcx.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token stored for funcx_service")

    auth_client = _make_auth_client()
    refreshed = auth_client.oauth2_refresh_token(refresh_token)
    refreshed_bundle = _extract_funcx_tokens(refreshed)
    access_token = refreshed_bundle["funcx_service"]["access_token"]
    return access_token, refreshed_bundle


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/login")
def login(
    clearml_user_id: str = Query(...),
    email: str = Query(...),
) -> RedirectResponse:
    auth_client = _make_auth_client()
    state_payload = {"clearml_user_id": clearml_user_id, "email": email}
    signed_state = state_signer.dumps(state_payload)

    auth_client.oauth2_start_flow(
        redirect_uri=settings.globus_redirect_uri,
        requested_scopes=settings.globus_scopes,
        refresh_tokens=True,
        state=signed_state,
    )
    return RedirectResponse(auth_client.oauth2_get_authorize_url())


@app.get("/callback")
def callback(code: str = Query(...), state: str = Query(...)) -> JSONResponse:
    try:
        payload = state_signer.loads(state)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid state: {exc}")

    auth_client = _make_auth_client()
    # Globus SDK signatures differ by version; redirect URI is already fixed in the
    # authorize request and should match app registration.
    try:
        token_response = auth_client.oauth2_exchange_code_for_tokens(code)
    except TypeError:
        token_response = auth_client.oauth2_exchange_code_for_tokens(
            code,
            redirect_uri=settings.globus_redirect_uri,
        )

    token_bundle = _extract_funcx_tokens(token_response)
    token_store.put_token_bundle(
        clearml_user_id=payload["clearml_user_id"],
        email=payload["email"],
        token_bundle=token_bundle,
    )

    return JSONResponse(
        {
            "status": "ok",
            "message": "Globus tokens stored for user",
            "clearml_user_id": payload["clearml_user_id"],
            "email": payload["email"],
        }
    )


@app.post("/submit")
def submit(
    body: SubmitRequest,
    x_connector_key: Optional[str] = Header(default=None),
) -> JSONResponse:
    _validate_submit_secret(x_connector_key)

    if body.clearml_task_id:
        _maybe_validate_task_owner(body.clearml_task_id, body.clearml_user_id)

    token_bundle = token_store.get_token_bundle(body.clearml_user_id)
    if not token_bundle:
        raise HTTPException(
            status_code=404,
            detail="No stored token for user. Complete /login -> /callback first.",
        )

    access_token, refreshed_bundle = _refresh_access_token(token_bundle)
    token_store.put_token_bundle(
        clearml_user_id=body.clearml_user_id,
        email=body.email,
        token_bundle=refreshed_bundle,
    )

    authorizer = globus_sdk.AccessTokenAuthorizer(access_token)
    compute_client = ComputeClient(authorizer=authorizer)
    with Executor(endpoint_id=body.endpoint_id, client=compute_client) as executor:
        future = executor.submit(operator.mul, body.input_value, body.input_value)
        result = future.result(timeout=body.timeout_sec)
        globus_task_id = str(getattr(future, "task_id", ""))

    return JSONResponse(
        {
            "status": "ok",
            "endpoint_id": body.endpoint_id,
            "globus_task_id": globus_task_id,
            "result": result,
        }
    )


@app.exception_handler(Exception)
def unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)})
