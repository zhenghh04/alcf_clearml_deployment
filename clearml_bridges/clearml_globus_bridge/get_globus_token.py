import argparse
import json
import os
import sqlite3
import subprocess
import time
import warnings
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print an export command for Globus Compute or Transfer access token."
    )
    parser.add_argument(
        "--type",
        dest="token_type",
        default="compute",
        choices=["compute", "transfer"],
        help="Token type to export (default: compute).",
    )
    parser.add_argument(
        "--login-if-needed",
        action="store_true",
        help="Run login flow before reading local token storage.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print only the token value (no export prefix).",
    )
    parser.add_argument(
        "--env-var",
        default="",
        help="Environment variable name for export output. Defaults by --type.",
    )
    return parser.parse_args()


def _get_compute_access_token() -> str:
    from globus_compute_sdk.sdk.login_manager.manager import LoginManager, ComputeScopes

    warnings.filterwarnings(
        "ignore",
        message="The `LoginManager` is deprecated.*",
        category=UserWarning,
    )
    login_manager = LoginManager()
    tokens = login_manager._token_storage.get_by_resource_server()
    token = tokens.get(ComputeScopes.resource_server, {}).get("access_token", "")
    return str(token).strip()


def _read_access_token_from_sqlite(db_path: Path, resource_servers: list[str]) -> str:
    if not db_path.exists():
        return ""

    try:
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        rows = cur.execute(
            "SELECT namespace, resource_server, token_data_json FROM token_storage"
        ).fetchall()
    except Exception:
        return ""
    finally:
        try:
            con.close()
        except Exception:
            pass

    # Prefer production namespaces and active tokens with latest expiry.
    ns_priority = {"user/production": 0, "userprofile/production": 0}
    rs_order = {rs: i for i, rs in enumerate(resource_servers)}
    now = int(time.time())
    candidates: list[tuple[int, int, int, str]] = []
    for namespace, resource_server, token_data_json in rows:
        if resource_server not in rs_order:
            continue
        try:
            parsed = json.loads(token_data_json)
        except Exception:
            continue
        token = str(parsed.get("access_token", "")).strip()
        if not token:
            continue
        expires_at = int(parsed.get("expires_at_seconds") or 0)
        # Keep non-expired tokens first; expired ones still considered as last resort.
        is_expired = 1 if expires_at and expires_at <= now else 0
        candidates.append(
            (
                rs_order[resource_server],
                ns_priority.get(str(namespace), 1),
                is_expired,
                -expires_at if expires_at else 0,
                token,
            )
        )
    if not candidates:
        return ""
    candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return candidates[0][4]


def _get_transfer_access_token() -> str:
    # Prefer official Globus CLI token storage if available.
    token = _read_access_token_from_sqlite(
        Path.home() / ".globus" / "cli" / "storage.db",
        resource_servers=["transfer.api.globus.org"],
    )
    if token:
        return token

    # Fallback: explicit env vars.
    return str(
        os.getenv("GLOBUS_TRANSFER_ACCESS_TOKEN")
        or os.getenv("GLOBUS_ACCESS_TOKEN")
        or ""
    ).strip()


def _run_compute_login() -> None:
    subprocess.run(
        ["globus-compute-endpoint", "login"],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _run_transfer_login() -> None:
    subprocess.run(
        ["globus", "login"],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _refresh_transfer_token_cache() -> None:
    # Best-effort refresh trigger for Globus CLI token cache.
    # If CLI is not logged in, this command may fail; caller handles empty token later.
    subprocess.run(
        ["globus", "whoami", "--format", "json"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    args = parse_args()
    token_type = args.token_type

    if args.login_if_needed:
        if token_type == "compute":
            _run_compute_login()
        else:
            _run_transfer_login()

    if token_type == "transfer":
        _refresh_transfer_token_cache()

    token = _get_compute_access_token() if token_type == "compute" else _get_transfer_access_token()
    if not token:
        if token_type == "compute":
            error_msg = (
                "ERROR: No Globus Compute access token found.\n"
                "Run:\n"
                "  globus-compute-endpoint login\n"
                "Then retry:\n"
                "  eval \"$(clearml-globus-token --type compute)\""
            )
        else:
            error_msg = (
                "ERROR: No Globus Transfer access token found.\n"
                "Run:\n"
                "  globus login --consent\n"
                "Then retry:\n"
                "  eval \"$(clearml-globus-token --type transfer)\""
            )
        print(
            error_msg,
            file=os.sys.stderr,
        )
        return 1

    if args.raw:
        print(token)
    else:
        default_env_var = (
            "GLOBUS_COMPUTE_ACCESS_TOKEN"
            if token_type == "compute"
            else "GLOBUS_TRANSFER_ACCESS_TOKEN"
        )
        env_var = args.env_var or default_env_var
        # Shell-safe single-quote escaping for POSIX shells.
        quoted = "'" + token.replace("'", "'\"'\"'") + "'"
        print(f"export {env_var}={quoted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
