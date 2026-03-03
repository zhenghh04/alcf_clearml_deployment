import argparse
import shutil
import subprocess
from pathlib import Path


CONFIG_TEMPLATE = """display_name: {endpoint_name}
engine:
  type: GlobusComputeEngine
  provider:
    type: SlurmProvider
    account: {account}
    partition: {partition}
    qos: {qos}
    walltime: {walltime}
    launcher:
      type: SrunLauncher
    nodes_per_block: {nodes_per_block}
    init_blocks: 0
    min_blocks: 0
    max_blocks: {max_blocks}
"""


USER_CONFIG_TEMPLATE = """# Dynamic per-submission overrides from user_endpoint_config.
# These values are consumed by Globus Compute when tasks are submitted
# with Executor(..., user_endpoint_config=...).

endpoint_setup: |
  source /etc/profile
  export PATH={endpoint_bin_dir}:{scheduler_bin_dir}:/usr/bin:/bin

engine:
  type: GlobusComputeEngine
  provider:
    type: SlurmProvider
    account: {{{{ account | default('{account}') }}}}
    partition: {{{{ partition | default('{partition}') }}}}
    qos: {{{{ qos | default('{qos}') }}}}
    walltime: {{{{ walltime | default('{walltime}') }}}}
    nodes_per_block: {{{{ num_nodes | default({nodes_per_block}) }}}}
    init_blocks: {{{{ init_blocks | default(0) }}}}
    min_blocks: {{{{ min_blocks | default(0) }}}}
    max_blocks: {{{{ max_blocks | default({template_max_blocks}) }}}}
    scheduler_options: |
      #SBATCH -A {{{{ account | default('{account}') }}}}
      #SBATCH -p {{{{ partition | default('{partition}') }}}}
      #SBATCH --qos={{{{ qos | default('{qos}') }}}}
      #SBATCH --nodes={{{{ num_nodes | default({nodes_per_block}) }}}}
      #SBATCH --time={{{{ walltime | default('{walltime}') }}}}
      #SBATCH --cpus-per-task={{{{ cores_per_node | default({cores_per_node}) }}}}
{gpus_line}{constraint_line}    worker_init: {{{{ worker_init | default() }}}}

idle_heartbeats_soft: 10
idle_heartbeats_hard: 5760
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create/update Globus Compute Slurm endpoint config files."
    )
    parser.add_argument("--endpoint-name", required=True, help="Endpoint directory name.")
    parser.add_argument(
        "--base-dir",
        default="~/.globus_compute",
        help="Base Globus Compute endpoint directory (default: ~/.globus_compute).",
    )
    parser.add_argument("--account", default="datascience")
    parser.add_argument("--partition", default="debug")
    parser.add_argument("--qos", default="normal")
    parser.add_argument("--walltime", default="00:10:00")
    parser.add_argument("--nodes-per-block", type=int, default=1)
    parser.add_argument("--max-blocks", type=int, default=1)
    parser.add_argument("--cores-per-node", type=int, default=64)
    parser.add_argument("--gpus-per-node", type=int, default=0)
    parser.add_argument("--constraint", default="")
    parser.add_argument(
        "--scheduler-bin-dir",
        default="/usr/bin",
        help="Directory containing slurm binaries (srun/sbatch).",
    )
    parser.add_argument(
        "--endpoint-bin-dir",
        default="",
        help="Directory containing globus-compute-endpoint. Auto-detected if omitted.",
    )
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


def main() -> int:
    args = parse_args()
    endpoint_bin_dir = args.endpoint_bin_dir.strip()
    if not endpoint_bin_dir:
        endpoint_cli = shutil.which("globus-compute-endpoint")
        endpoint_bin_dir = str(Path(endpoint_cli).parent) if endpoint_cli else "/usr/bin"

    login_result = "skip endpoint login (requested)"
    if args.login_first:
        subprocess.run(["globus-compute-endpoint", "login"], check=True)
        login_result = "run globus-compute-endpoint login"

    base_dir = Path(args.base_dir).expanduser()
    endpoint_dir = base_dir / args.endpoint_name
    endpoint_dir.mkdir(parents=True, exist_ok=True)

    config_path = endpoint_dir / "config.yaml"
    user_template_path = endpoint_dir / "user_config_template.yaml.j2"

    config_content = CONFIG_TEMPLATE.format(
        endpoint_name=args.endpoint_name,
        account=args.account,
        partition=args.partition,
        qos=args.qos,
        walltime=args.walltime,
        nodes_per_block=args.nodes_per_block,
        max_blocks=args.max_blocks,
    )

    gpus_line = ""
    if args.gpus_per_node > 0:
        gpus_line = (
            "      #SBATCH --gpus-per-node="
            f"{{{{ gpus_per_node | default({args.gpus_per_node}) }}}}\n"
        )

    constraint_line = ""
    if args.constraint.strip():
        escaped_constraint = args.constraint.strip().replace("'", "\\'")
        constraint_line = (
            "      #SBATCH --constraint="
            f"{{{{ constraint | default('{escaped_constraint}') }}}}\n"
        )

    user_template_content = USER_CONFIG_TEMPLATE.format(
        account=args.account,
        partition=args.partition,
        qos=args.qos,
        walltime=args.walltime,
        nodes_per_block=args.nodes_per_block,
        cores_per_node=args.cores_per_node,
        gpus_line=gpus_line,
        constraint_line=constraint_line,
        template_max_blocks=args.max_blocks,
        endpoint_bin_dir=endpoint_bin_dir,
        scheduler_bin_dir=args.scheduler_bin_dir,
    )

    results = [
        login_result,
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
    print("3) verify generated submit script contains '#SBATCH --nodes=' lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
