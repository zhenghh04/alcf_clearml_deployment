import argparse
import math

from clearml import PipelineController, Task


def build_node_groups(num_nodes: int, nodes_per_task: int) -> list[list[str]]:
    nodes = [f"node-{idx}" for idx in range(1, num_nodes + 1)]
    return [nodes[i : i + nodes_per_task] for i in range(0, len(nodes), nodes_per_task)]


def create_template_task(queue: str, account: str, walltime: str) -> Task:
    task = Task.create(
        project_name="AmSC",
        task_name="Ensamble pipeline template",
        task_type=Task.TaskTypes.training,
        repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
        branch="main",
        script="examples/job_launching/ensamble/subtask_worker.py",
        working_directory="./",
        binary="python",
    )
    task.set_user_properties(walltime=walltime, account=account, queue=queue)
    return task


def create_join_task(queue: str, account: str, walltime: str) -> Task:
    task = Task.create(
        project_name="AmSC",
        task_name="Ensamble join",
        task_type=Task.TaskTypes.training,
        repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
        branch="main",
        script="examples/job_launching/ensamble/subtask_worker.py",
        working_directory="./",
        binary="python",
        argparse_args=[("--task-index", "-1"), ("--nodes", "join")],
    )
    task.set_user_properties(walltime=walltime, account=account, queue=queue)
    return task


def launch_pipeline_mode(args: argparse.Namespace) -> None:
    groups = build_node_groups(args.num_nodes, args.nodes_per_task)
    if not groups:
        raise ValueError("No node groups generated. Check --num-nodes and --nodes-per-task")

    pipeline = PipelineController(
        project=args.project,
        name=args.pipeline_name,
        version="1.0",
        add_pipeline_tags=False,
    )

    template = create_template_task(args.queue, args.account, args.walltime)
    step_names: list[str] = []
    for idx, node_group in enumerate(groups):
        step_name = f"subtask_{idx}"
        step_names.append(step_name)
        pipeline.add_step(
            name=step_name,
            base_task_id=template.id,
            execution_queue=args.queue,
            parameter_override={
                "Args/task_index": str(idx),
                "Args/nodes": ",".join(node_group),
            },
        )

    join_task = create_join_task(args.queue, args.account, args.walltime)
    pipeline.add_step(
        name="join",
        base_task_id=join_task.id,
        execution_queue=args.queue,
        parents=step_names,
    )

    pipeline.start(queue=args.queue)
    print(f"Started pipeline '{args.pipeline_name}' on queue '{args.queue}'")
    print(f"Pipeline task id: {pipeline.id}")
    if hasattr(pipeline, "get_output_log_web_page"):
        try:
            print(f"Pipeline results: {pipeline.get_output_log_web_page()}")
        except Exception:
            pass


def launch_single_allocation_mode(args: argparse.Namespace) -> None:
    task = Task.create(
        project_name=args.project,
        task_name=args.runner_name,
        task_type=Task.TaskTypes.training,
        repo="git@github.com:zhenghh04/alcf_clearml_deployment.git",
        branch="main",
        script="examples/job_launching/ensamble/run_local_tasks.py",
        working_directory="./",
        binary="python",
        argparse_args=[
            ("--tasks", str(max(1, math.ceil(args.num_nodes / args.nodes_per_task)))),
            ("--nodes-per-task", str(args.nodes_per_task)),
        ],
    )
    task.set_user_properties(
        walltime=args.walltime,
        num_nodes=args.num_nodes,
        account=args.account,
        queue=args.queue,
    )
    Task.enqueue(task, queue_name=args.queue)
    print(f"Enqueued single-allocation runner on queue '{args.queue}'")
    print(f"Runner task id: {task.id}")
    if hasattr(task, "get_output_log_web_page"):
        try:
            print(f"Runner results: {task.get_output_log_web_page()}")
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("pipeline", "single-allocation"),
        default="pipeline",
        help=(
            "pipeline: each subtask is a pipeline step with independent queue allocation; "
            "single-allocation: one queued runner gets all nodes once and launches internal subtasks."
        ),
    )
    parser.add_argument("--queue", default="crux-services")
    parser.add_argument("--num-nodes", type=int, default=6)
    parser.add_argument("--nodes-per-task", type=int, default=2)
    parser.add_argument("--walltime", default="00:30:00")
    parser.add_argument("--account", default="datascience")
    parser.add_argument("--project", default="AmSC")
    parser.add_argument("--pipeline-name", default="Ensamble pipeline")
    parser.add_argument("--runner-name", default="Ensamble runner")
    args = parser.parse_args()

    if args.mode == "pipeline":
        launch_pipeline_mode(args)
        return
    launch_single_allocation_mode(args)


if __name__ == "__main__":
    main()
