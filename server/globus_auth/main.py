import json
import os
import operator
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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
    print_refreshed_token: bool


class SubmitRequest(BaseModel):
    clearml_user_id: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    endpoint_id: str = Field(..., min_length=1)
    input_value: int = 7
    timeout_sec: int = 1800
    poll_interval: int = 5
    clearml_task_id: Optional[str] = None
    script: str = ""
    script_args: List[str] = Field(default_factory=list)
    binary: str = "/bin/bash"
    working_directory: str = ""
    repo_url: str = ""
    repo_branch: str = ""
    repo_working_directory: str = ""
    clone_repo: bool = False
    endpoint_config: Dict[str, Any] = Field(default_factory=dict)
    submit_retries: int = 2
    retry_backoff_sec: int = 5


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
        connector_db_path=os.getenv("CONNECTOR_DB_PATH", "server/globus_auth/tokens.db"),
        connector_fernet_key=os.environ["CONNECTOR_FERNET_KEY"],
        connector_base_url=os.getenv("CONNECTOR_BASE_URL", "http://localhost:8000"),
        connector_shared_secret=os.getenv("CONNECTOR_SHARED_SECRET", ""),
        strict_clearml_owner_check=os.getenv("STRICT_CLEARML_OWNER_CHECK", "false").lower()
        == "true",
        print_refreshed_token=os.getenv("PRINT_REFRESHED_TOKEN", "false").lower() == "true",
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
    if settings.print_refreshed_token:
        print(json.dumps(refreshed_bundle["funcx_service"], indent=2), flush=True)
    return access_token, refreshed_bundle


def _is_retryable_submission_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    retry_tokens = [
        "endpoint_not_online",
        "disconnected",
        "connection closed",
        "temporarily unavailable",
        "timed out",
        "timeout",
    ]
    non_retry_tokens = [
        "access_refused",
        "invalid credentials",
        "authentication",
        "resource: filesystems is required",
        "resource_conflict",
    ]
    if any(t in msg for t in non_retry_tokens):
        return False
    return any(t in msg for t in retry_tokens)


def _run_script(
    script_path: str,
    script_args: List[str],
    binary: str,
    working_directory: Optional[str],
    repo_url: Optional[str],
    repo_branch: Optional[str],
    repo_working_directory: Optional[str],
    clone_repo: bool,
) -> Dict[str, Any]:
    # Keep imports inside the remotely executed function to avoid missing globals
    # when deserialized on endpoint workers with different Python environments.
    import os
    import subprocess
    import tempfile

    checkout_root = ""
    run_cwd = working_directory or None
    resolved_script_path = script_path

    if clone_repo:
        if not repo_url:
            raise ValueError("clone_repo is enabled but repo_url is empty")
        checkout_root = tempfile.mkdtemp(prefix="globus_repo_")
        clone_cmd = ["git", "clone", "--depth", "1", repo_url, checkout_root]
        if repo_branch:
            clone_cmd = ["git", "clone", "--depth", "1", "--branch", repo_branch, repo_url, checkout_root]
        clone_completed = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if clone_completed.returncode != 0:
            return {
                "mode": "remote_script",
                "clone_repo": True,
                "repo_url": repo_url,
                "repo_branch": repo_branch,
                "clone_command": clone_cmd,
                "return_code": clone_completed.returncode,
                "stdout": clone_completed.stdout,
                "stderr": clone_completed.stderr,
            }

        run_cwd = checkout_root
        if repo_working_directory:
            repo_rel_dir = repo_working_directory.lstrip("./")
            run_cwd = os.path.join(checkout_root, repo_rel_dir)
        resolved_script_path = (
            script_path
            if os.path.isabs(script_path)
            else os.path.join(checkout_root, script_path.lstrip("./"))
        )
    elif run_cwd and not os.path.isabs(script_path):
        resolved_script_path = os.path.join(run_cwd, script_path.lstrip("./"))

    cmd = [binary, resolved_script_path] + script_args
    completed = subprocess.run(
        cmd,
        cwd=run_cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "mode": "remote_script",
        "command": cmd,
        "clone_repo": clone_repo,
        "repo_url": repo_url,
        "repo_branch": repo_branch,
        "repo_working_directory": repo_working_directory,
        "resolved_script_path": resolved_script_path,
        "cwd": run_cwd,
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


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
    auth_client.oauth2_start_flow(
        redirect_uri=settings.globus_redirect_uri,
        requested_scopes=settings.globus_scopes,
        refresh_tokens=True,
    )
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
    max_attempts = max(1, body.submit_retries + 1)
    start = time.time()
    output_value: Any = None
    globus_task_id = ""
    for attempt in range(1, max_attempts + 1):
        try:
            with Executor(
                endpoint_id=body.endpoint_id,
                client=compute_client,
                user_endpoint_config=body.endpoint_config or None,
            ) as executor:
                if body.script:
                    future = executor.submit(
                        _run_script,
                        body.script,
                        body.script_args,
                        body.binary,
                        body.working_directory or None,
                        body.repo_url or None,
                        body.repo_branch or None,
                        body.repo_working_directory or None,
                        body.clone_repo,
                    )
                else:
                    future = executor.submit(operator.mul, body.input_value, body.input_value)

                globus_task_id = str(getattr(future, "task_id", ""))
                while not future.done():
                    elapsed = time.time() - start
                    if elapsed > body.timeout_sec:
                        raise TimeoutError(
                            f"Timed out waiting for Globus task after {body.timeout_sec}s"
                        )
                    time.sleep(max(1, body.poll_interval))
                output_value = future.result()
            break
        except Exception as exc:
            if attempt >= max_attempts or not _is_retryable_submission_error(exc):
                raise
            time.sleep(max(1, body.retry_backoff_sec * attempt))

    if body.script and isinstance(output_value, dict) and output_value.get("return_code", 1) != 0:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Remote script failed with return code {output_value.get('return_code')}: "
                f"{output_value.get('stderr', '')}"
            ),
        )

    return JSONResponse(
        {
            "status": "ok",
            "endpoint_id": body.endpoint_id,
            "globus_task_id": globus_task_id,
            "result": output_value,
            "mode": "script" if body.script else "default_multiply",
        }
    )


@app.exception_handler(Exception)
def unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)})
