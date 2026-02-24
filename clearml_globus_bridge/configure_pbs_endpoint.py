import argparse
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
        action="store_true",
        help="Overwrite existing files. If omitted, existing files are kept.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak copies before overwriting.",
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


def main() -> int:
    args = parse_args()
    base_dir = Path(args.base_dir).expanduser()
    endpoint_dir = base_dir / args.endpoint_name
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
