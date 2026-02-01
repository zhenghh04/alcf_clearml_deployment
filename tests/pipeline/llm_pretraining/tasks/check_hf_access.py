import argparse
import os
import sys

from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        default=os.environ.get("HF_DATASET", "nvidia/Nemotron-Pretraining-Code-v2"),
    )
    args = parser.parse_args()

    dataset = args.dataset
    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token)

    try:
        info = api.dataset_info(dataset)
    except HfHubHTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")
        print(f"[hf-access] ERROR: cannot access {dataset} (HTTP {status}).")
        print("[hf-access] If this dataset is gated, request access and set HF_TOKEN.")
        return 1
    except Exception as exc:
        print(f"[hf-access] ERROR: failed to query {dataset}: {exc}")
        return 1

    gated = getattr(info, "gated", None)
    if gated in ("manual", True):
        print(f"[hf-access] {dataset} is gated: {gated}")
        if not token:
            print("[hf-access] HF_TOKEN not set; access likely not granted.")
            return 1
        print("[hf-access] HF_TOKEN provided; access appears granted.")
        return 0

    print(f"[hf-access] {dataset} is not gated (gated={gated}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
