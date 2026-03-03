import argparse

from clearml import Task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-min-output", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    task = Task.init(
        project_name="amsc/pipeline-globus-bridge",
        task_name="postprocess-globus-results",
        task_type=Task.TaskTypes.testing,
    )
    task.connect(vars(args), name="postprocess")

    logger = task.get_logger()
    logger.report_text(
        "Postprocess step placeholder: validate or transform Globus outputs here."
    )
    logger.report_scalar(
        "postprocess", "expected_min_output", value=args.expected_min_output, iteration=0
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
