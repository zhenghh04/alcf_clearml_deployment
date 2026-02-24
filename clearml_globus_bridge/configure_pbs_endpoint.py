import argparse
import os
import subprocess
from pathlib import Path


CONFIG_TEMPLATE = """display_name: {endpoint_name}
engine:
  type: GlobusComputeEngine
  provider:
    type: PBSProProvider
    account: {account}
    queue: {queue}
    walltime: {walltime}
    launcher:
      type: SimpleLauncher
    nodes_per_block: {nodes_per_block}
    init_blocks: 0
    min_blocks: 0
    max_blocks: {max_blocks}
"""


USER_CONFIG_TEMPLATE = """# Dynamic per-submission overrides from user_endpoint_config.
# These values are consumed by Globus Compute when tasks are submitted
# with Executor(..., user_endpoint_config=...).

endpoint_setup: {{ endpoint_setup | default() }}

engine:
  provider:
    account: "{{{{ account | default('{account}') }}}}"
    queue: "{{{{ queue | default('{queue}') }}}}"
    walltime: "{{{{ walltime | default('{walltime}') }}}}"
    nodes_per_block: {{{{ num_nodes | default({nodes_per_block}) }}}}
    scheduler_options: |
      #PBS -l select={{{{ num_nodes | default({nodes_per_block}) }}}}:ncpus={{{{ cores_per_node | default({cores_per_node}) }}}}
      #PBS -l walltime={{{{ walltime | default('{walltime}') }}}}
      #PBS -l filesystems={{{{ filesystems | default('{filesystems}') }}}}
    worker_init: {{{{ worker_init | default() }}}}

idle_heartbeats_soft: 10
idle_heartbeats_hard: 5760
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create/update Globus Compute PBS endpoint config files."
    )
    parser.add_argument("--endpoint-name", required=True, help="Endpoint directory name.")
    parser.add_argument(
        "--base-dir",
        default="~/.globus_compute",
        help="Base Globus Compute endpoint directory (default: ~/.globus_compute).",
    )
    parser.add_argument("--account", default="datascience")
    parser.add_argument("--queue", default="debug")
    parser.add_argument("--walltime", default="00:10:00")
    parser.add_argument("--nodes-per-block", type=int, default=1)
    parser.add_argument("--max-blocks", type=int, default=1)
    parser.add_argument("--cores-per-node", type=int, default=64)
    parser.add_argument("--filesystems", default="flare:home")
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        default=True,
        help="Overwrite existing files (default: enabled).",
    )
    parser.add_argument(
        "--no-overwrite",
        dest="overwrite",
        action="store_false",
        help="Do not overwrite existing files.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak copies before overwriting.",
    )
    parser.add_argument(
        "--skip-endpoint-configure",
        action="store_true",
        help="Skip running 'globus-compute-endpoint configure <endpoint-name>'.",
    )
    parser.add_argument(
        "--skip-login",
        dest="login_first",
        action="store_false",
        default=True,
        help="Skip running 'globus-compute-endpoint login' first.",
    )
    return parser.parse_args()


def maybe_backup(path: Path, enable_backup: bool) -> None:
    if enable_backup and path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def write_if_allowed(path: Path, content: str, overwrite: bool, backup: bool) -> str:
    if path.exists() and not overwrite:
        return f"skip {path} (already exists; use --overwrite)"
    maybe_backup(path, backup)
    path.write_text(content, encoding="utf-8")
    return f"write {path}"


def configure_endpoint(base_dir: Path, endpoint_name: str, skip: bool) -> str:
    if skip:
        return "skip endpoint configure (requested)"

    cmd = ["globus-compute-endpoint", "configure", endpoint_name]
    env = os.environ.copy()
    env.setdefault("GLOBUS_COMPUTE_USER_DIR", str(base_dir))
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    if completed.returncode == 0:
        return f"run {' '.join(cmd)}"

    combined = f"{completed.stdout}\n{completed.stderr}".lower()
    if "already exists" in combined or "exists already" in combined:
        return "skip endpoint configure (already exists)"

    raise RuntimeError(
        "Failed to configure endpoint with "
        f"'{' '.join(cmd)}' (exit={completed.returncode}).\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )


def main() -> int:
    args = parse_args()
    login_result = "skip endpoint login (requested)"
    if args.login_first:
        subprocess.run(["globus-compute-endpoint", "login"], check=True)
        login_result = "run globus-compute-endpoint login"

    base_dir = Path(args.base_dir).expanduser()
    endpoint_dir = base_dir / args.endpoint_name
    configure_result = configure_endpoint(
        base_dir=base_dir,
        endpoint_name=args.endpoint_name,
        skip=args.skip_endpoint_configure,
    )
    endpoint_dir.mkdir(parents=True, exist_ok=True)

    config_path = endpoint_dir / "config.yaml"
    user_template_path = endpoint_dir / "user_config_template.yaml.j2"

    config_content = CONFIG_TEMPLATE.format(
        endpoint_name=args.endpoint_name,
        account=args.account,
        queue=args.queue,
        walltime=args.walltime,
        nodes_per_block=args.nodes_per_block,
        max_blocks=args.max_blocks,
    )

    user_template_content = USER_CONFIG_TEMPLATE.format(
        account=args.account,
        queue=args.queue,
        walltime=args.walltime,
        nodes_per_block=args.nodes_per_block,
        cores_per_node=args.cores_per_node,
        filesystems=args.filesystems,
    )

    results = [
        login_result,
        configure_result,
        write_if_allowed(
            config_path,
            config_content,
            overwrite=args.overwrite,
            backup=args.backup,
        ),
        write_if_allowed(
            user_template_path,
            user_template_content,
            overwrite=args.overwrite,
            backup=args.backup,
        ),
    ]

    print(f"endpoint_dir={endpoint_dir}")
    for line in results:
        print(line)
    print("\nNext steps:")
    print(f"1) globus-compute-endpoint stop {args.endpoint_name}")
    print(f"2) globus-compute-endpoint start {args.endpoint_name}")
    print("3) verify generated submit script contains '#PBS -l select=' lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
