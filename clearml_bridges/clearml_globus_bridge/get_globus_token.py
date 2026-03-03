import argparse
import os
import subprocess
import warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print an export command for GLOBUS_COMPUTE_ACCESS_TOKEN."
    )
    parser.add_argument(
        "--login-if-needed",
        action="store_true",
        help="Run 'globus-compute-endpoint login' before reading local token storage.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print only the token value (no export prefix).",
    )
    parser.add_argument(
        "--env-var",
        default="GLOBUS_COMPUTE_ACCESS_TOKEN",
        help="Environment variable name for export output (default: GLOBUS_COMPUTE_ACCESS_TOKEN).",
    )
    return parser.parse_args()


def _get_access_token() -> str:
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


def _run_login() -> None:
    subprocess.run(
        ["globus-compute-endpoint", "login"],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def main() -> int:
    args = parse_args()

    if args.login_if_needed:
        _run_login()

    token = _get_access_token()
    if not token:
        print(
            "ERROR: No Globus Compute access token found.\n"
            "Run:\n"
            "  globus-compute-endpoint login\n"
            "Then retry:\n"
            "  eval \"$(clearml-globus-token)\"",
            file=os.sys.stderr,
        )
        return 1

    if args.raw:
        print(token)
    else:
        # Shell-safe single-quote escaping for POSIX shells.
        quoted = "'" + token.replace("'", "'\"'\"'") + "'"
        print(f"export {args.env_var}={quoted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
