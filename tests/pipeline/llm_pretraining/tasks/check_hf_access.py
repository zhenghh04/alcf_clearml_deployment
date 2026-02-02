import argparse
import os
import sys
import time

from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        default=os.environ.get("HF_DATASET", "nvidia/Nemotron-Pretraining-Code-v2"),
    )
    parser.add_argument(
        "--repo-type",
        default=os.environ.get("HF_REPO_TYPE", "dataset"),
        choices=("dataset", "model", "space"),
        help="Hugging Face repo type to check.",
    )
    parser.add_argument(
        "--probe-file",
        default=os.environ.get("HF_PROBE_FILE"),
        help="File to download to verify access (small file recommended).",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=int(os.environ.get("HF_POLL_INTERVAL_SEC", "600")),
        help="Seconds to wait between access checks.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=int(os.environ.get("HF_MAX_ATTEMPTS", "0")),
        help="Max attempts before failing (0 = retry forever).",
    )
    args = parser.parse_args()

    dataset = args.dataset
    repo_type = args.repo_type
    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token)
    attempt = 0
    try:
        if token:
            who = api.whoami()
            print(f"[hf-access] token user: {who.get('name') or who.get('email') or who}")
        else:
            print("[hf-access] HF_TOKEN not set")
    except Exception as exc:
        print(f"[hf-access] WARNING: failed to resolve token identity: {exc}")

    while True:
        attempt += 1
        try:
            info = api.repo_info(dataset, repo_type=repo_type)
        except HfHubHTTPError as exc:
            status = getattr(exc.response, "status_code", "unknown")
            print(
                f"[hf-access] ERROR: cannot access {dataset} (repo_type={repo_type}, HTTP {status})."
            )
            print("[hf-access] If this dataset is gated, request access and set HF_TOKEN.")
            if args.max_attempts and attempt >= args.max_attempts:
                return 1
            print(f"[hf-access] Waiting {args.poll_interval}s before retry...")
            time.sleep(args.poll_interval)
            continue
        except Exception as exc:
            print(f"[hf-access] ERROR: failed to query {dataset}: {exc}")
            if args.max_attempts and attempt >= args.max_attempts:
                return 1
            print(f"[hf-access] Waiting {args.poll_interval}s before retry...")
            time.sleep(args.poll_interval)
            continue

        gated = getattr(info, "gated", None)
        private = getattr(info, "private", None)
        requires_token = gated in ("manual", True) or private is True
        if requires_token and not token:
            print(
                f"[hf-access] {dataset} requires token (gated={gated}, private={private})."
            )
            print("[hf-access] HF_TOKEN not set; access not granted.")
            if args.max_attempts and attempt >= args.max_attempts:
                return 1
            print(f"[hf-access] Waiting {args.poll_interval}s for approval or token...")
            time.sleep(args.poll_interval)
            continue

        try:
            files = api.list_repo_files(dataset, repo_type=repo_type)
        except HfHubHTTPError as exc:
            status = getattr(exc.response, "status_code", "unknown")
            print(f"[hf-access] ERROR: token lacks access (HTTP {status}).")
            if args.max_attempts and attempt >= args.max_attempts:
                return 1
            print(f"[hf-access] Waiting {args.poll_interval}s for approval...")
            time.sleep(args.poll_interval)
            continue
        except Exception as exc:
            print(f"[hf-access] ERROR: failed to verify access: {exc}")
            if args.max_attempts and attempt >= args.max_attempts:
                return 1
            print(f"[hf-access] Waiting {args.poll_interval}s before retry...")
            time.sleep(args.poll_interval)
            continue

        probe = args.probe_file
        if not probe:
            if repo_type == "dataset":
                probe = ".gitattributes"
            elif repo_type == "model":
                probe = "config.json"
            else:
                probe = "README.md"
        if probe and probe in files:
            try:
                api.hf_hub_download(
                    dataset, filename=probe, repo_type=repo_type, token=token
                )
            except HfHubHTTPError as exc:
                status = getattr(exc.response, "status_code", "unknown")
                print(f"[hf-access] ERROR: download denied (HTTP {status}).")
                if args.max_attempts and attempt >= args.max_attempts:
                    return 1
                print(f"[hf-access] Waiting {args.poll_interval}s for approval...")
                time.sleep(args.poll_interval)
                continue
            except Exception as exc:
                print(f"[hf-access] ERROR: failed to download probe file: {exc}")
                if args.max_attempts and attempt >= args.max_attempts:
                    return 1
                print(f"[hf-access] Waiting {args.poll_interval}s before retry...")
                time.sleep(args.poll_interval)
                continue
        elif probe:
            print(f"[hf-access] WARNING: probe file not found: {probe}")

        print(f"[hf-access] Access to {args.dataset} verified.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
