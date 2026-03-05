import argparse
import json
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List Globus Compute endpoints visible to your identity."
    )
    parser.add_argument(
        "--token",
        default="",
        help=(
            "Globus access token for non-interactive auth. "
            "If omitted, GLOBUS_COMPUTE_ACCESS_TOKEN is used when set; "
            "otherwise default SDK auth flow is used."
        ),
    )
    parser.add_argument(
        "--role",
        default="any",
        choices=["any", "owner"],
        help="Endpoint visibility scope (default: any).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw endpoint list as JSON.",
    )
    parser.add_argument(
        "--no-metadata-lookup",
        action="store_true",
        help="Skip per-endpoint metadata lookup for entries with unknown state.",
    )
    parser.add_argument(
        "--debug-status",
        action="store_true",
        help="Print extracted status tokens for troubleshooting unknown state.",
    )
    return parser.parse_args()


def clean_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _compute_sdk_compat_error(exc: Exception) -> RuntimeError:
    return RuntimeError(
        "Incompatible Globus package versions detected for Compute SDK.\n"
        f"Original error: {exc}\n"
        "Fix with:\n"
        "  python -m pip install --upgrade \"globus-sdk>=3.59.0,<4\" \"globus-compute-sdk>=4.6.0\""
    )


def build_compute_client(access_token: str = "") -> Any:
    try:
        from globus_compute_sdk import Client
    except ImportError as exc:
        raise _compute_sdk_compat_error(exc) from exc

    token = clean_str(access_token)
    if not token:
        return Client(do_version_check=False)

    import globus_sdk

    return Client(
        authorizer=globus_sdk.AccessTokenAuthorizer(token),
        do_version_check=False,
    )


def resolve_state(endpoint: Dict[str, Any]) -> str:
    status_tokens = collect_status_tokens(endpoint)
    joined = " ".join(token.lower() for token in status_tokens if token)
    if not joined:
        return "unknown"

    running_tokens = {"online", "running", "active", "connected", "ready"}
    stopped_tokens = {"offline", "stopped", "inactive", "disconnected", "error", "failed", "paused"}
    if any(token in joined for token in running_tokens):
        return "running"
    if any(token in joined for token in stopped_tokens):
        return "stopped"
    return "unknown"


def collect_status_tokens(payload: Any, max_depth: int = 6) -> List[str]:
    tokens: List[str] = []

    def _walk(value: Any, key_name: str = "", depth: int = 0) -> None:
        if depth > max_depth:
            return

        key = clean_str(key_name).lower()
        if isinstance(value, dict):
            for k, v in value.items():
                _walk(v, key_name=clean_str(k), depth=depth + 1)
            return

        if isinstance(value, list):
            for item in value:
                _walk(item, key_name=key_name, depth=depth + 1)
            return

        # Explicit booleans often appear as is_online / connected.
        if isinstance(value, bool):
            if key in {"online", "is_online", "connected", "is_connected"}:
                tokens.append("online" if value else "offline")
            return

        text = clean_str(value)
        if not text:
            return

        # Only capture values that are likely status-like to avoid noise.
        if key in {
            "status",
            "state",
            "endpoint_status",
            "connection_status",
            "health",
            "message",
            "reason",
            "status_code",
            "status_message",
        } or "status" in key or "state" in key:
            tokens.append(text)
            return

        lowered = text.lower()
        if lowered in {
            "online",
            "offline",
            "running",
            "stopped",
            "active",
            "inactive",
            "connected",
            "disconnected",
            "ready",
            "error",
            "failed",
        }:
            tokens.append(text)

    _walk(payload)
    return tokens


def normalize_endpoint(endpoint: Dict[str, Any]) -> Dict[str, str]:
    status_tokens = collect_status_tokens(endpoint)
    raw_status = "; ".join(dict.fromkeys(status_tokens))
    return {
        "name": clean_str(
            endpoint.get("display_name")
            or endpoint.get("name")
            or endpoint.get("endpoint_name")
        ),
        "id": clean_str(
            endpoint.get("uuid")
            or endpoint.get("id")
            or endpoint.get("endpoint_id")
        ),
        "state": resolve_state(endpoint),
        "status": raw_status,
        "owner": clean_str(endpoint.get("owner") or endpoint.get("owner_string")),
        "_tokens": raw_status,
    }


def enrich_unknown_state_endpoints(client: Any, endpoints: List[Dict[str, str]]) -> None:
    for item in endpoints:
        if item.get("state") != "unknown":
            continue
        endpoint_id = clean_str(item.get("id"))
        if not endpoint_id:
            continue
        lookup_payload: Dict[str, Any] = {"endpoint_id": endpoint_id}
        for fetcher_name in ("get_endpoint_status", "get_endpoint_metadata"):
            fetcher = getattr(client, fetcher_name, None)
            if not callable(fetcher):
                continue
            try:
                data = fetcher(endpoint_id) or {}
            except Exception:
                continue
            if isinstance(data, dict):
                lookup_payload[fetcher_name] = data
        normalized = normalize_endpoint(lookup_payload)
        if normalized.get("state") != "unknown":
            item["state"] = normalized.get("state", item["state"])
        if normalized.get("status"):
            item["status"] = normalized.get("status", item["status"])


def print_table(endpoints: List[Dict[str, str]]) -> None:
    if not endpoints:
        print("No endpoints found.")
        return
    name_width = max(4, max(len(item["name"]) for item in endpoints))
    id_width = max(2, max(len(item["id"]) for item in endpoints))
    state_width = max(5, max(len(item["state"]) for item in endpoints))
    status_width = max(6, max(len(item["status"]) for item in endpoints))
    owner_width = max(5, max(len(item["owner"]) for item in endpoints))

    header = (
        f"{'NAME'.ljust(name_width)}  "
        f"{'ID'.ljust(id_width)}  "
        f"{'STATE'.ljust(state_width)}  "
        f"{'STATUS'.ljust(status_width)}  "
        f"{'OWNER'.ljust(owner_width)}"
    )
    print(header)
    print("-" * len(header))
    for item in endpoints:
        print(
            f"{item['name'].ljust(name_width)}  "
            f"{item['id'].ljust(id_width)}  "
            f"{item['state'].ljust(state_width)}  "
            f"{item['status'].ljust(status_width)}  "
            f"{item['owner'].ljust(owner_width)}"
        )


def main() -> int:
    args = parse_args()
    import os

    token = clean_str(args.token) or clean_str(os.getenv("GLOBUS_COMPUTE_ACCESS_TOKEN"))
    try:
        client = build_compute_client(token)
    except RuntimeError as exc:
        print(str(exc), file=os.sys.stderr)
        return 1
    endpoints = client.get_endpoints(role=args.role) or []
    normalized = [normalize_endpoint(item) for item in endpoints]
    if not args.no_metadata_lookup:
        enrich_unknown_state_endpoints(client, normalized)
    normalized.sort(key=lambda item: (item["name"].lower(), item["id"].lower()))

    if args.debug_status:
        for item in normalized:
            print(
                f"[debug] id={item.get('id')} name={item.get('name')} "
                f"state={item.get('state')} tokens={item.get('status')}"
            )

    if args.json:
        cleaned = [{k: v for k, v in item.items() if not k.startswith("_")} for item in normalized]
        print(json.dumps(cleaned, indent=2))
    else:
        print_table(normalized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
