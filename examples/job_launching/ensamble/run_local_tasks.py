import argparse
import os
import subprocess
import sys
from pathlib import Path

from clearml import Task


def read_nodes() -> list[str]:
    nodefile = os.environ.get("PBS_NODEFILE") or os.environ.get("COBALT_NODEFILE")
    if nodefile and Path(nodefile).exists():
        with open(nodefile, "r", encoding="utf-8") as handle:
            return [line.strip() for line in handle if line.strip()]
    return [f"node-{idx}" for idx in range(1, 7)]


def chunk_nodes(nodes: list[str], group_size: int) -> list[list[str]]:
    return [nodes[i : i + group_size] for i in range(0, len(nodes), group_size)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=int, default=3)
    parser.add_argument("--nodes-per-task", type=int, default=2)
    args = parser.parse_args()

    task = Task.init(
        project_name="AmSC",
        task_name="Pattern B: runner",
        task_type=Task.TaskTypes.training,
    )
    logger = task.get_logger()

    nodes = read_nodes()
    logger.report_text(f"Detected nodes: {nodes}")

    groups = chunk_nodes(nodes, args.nodes_per_task)
    if len(groups) < args.tasks:
        logger.report_text(
            "Requested more tasks than available node groups; reducing task count."
        )
    task_count = min(args.tasks, len(groups))

    procs: list[subprocess.Popen] = []
    for idx in range(task_count):
        node_group = groups[idx]
        cmd = [
            sys.executable,
            "examples/job_launching/pattern_b/subtask_worker.py",
            "--task-index",
            str(idx),
            "--nodes",
            ",".join(node_group),
        ]
        logger.report_text(f"Launching subtask {idx} on nodes {node_group}")
        procs.append(subprocess.Popen(cmd))

    exit_codes = [proc.wait() for proc in procs]
    logger.report_text(f"Subtask exit codes: {exit_codes}")
    if any(code != 0 for code in exit_codes):
        raise SystemExit("One or more subtasks failed")


if __name__ == "__main__":
    main()