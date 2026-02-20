import argparse
import operator

from globus_compute_sdk import Executor

# This script is intended to be run from your remote machine

# Scripts adapted from Globus Compute docs
# https://globus-compute.readthedocs.io/en/latest/quickstart.html

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--endpoint-id",
        default="fad4d968-8c9a-45ce-9fb4-60a9ab90be60",
        help="Globus Compute endpoint ID.",
    )
    parser.add_argument("--a", type=int, default=5)
    parser.add_argument("--b", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    my_config = {"account": "datascience"}

    with Executor(endpoint_id=args.endpoint_id, user_endpoint_config=my_config) as gce:
        # Use stdlib builtin function to avoid Python bytecode compatibility issues
        # across local and endpoint minor-version differences.
        future = gce.submit(operator.add, args.a, args.b)
        print("Submitted task to remote endpoint, waiting for result...")
        print(f"Remote result returned: add_func result={future.result()}")


if __name__ == "__main__":
    main()
