import argparse
from clearml import Task


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--epochs", type=int, default=10)
    args = parser.parse_args()

    task = Task.init(project_name="amsc/ensemble-demo", task_name="train-model-a")
    task.connect(args)

    print(f"[train_a] Training model A (lr={args.learning_rate}, epochs={args.epochs})")


if __name__ == "__main__":
    main()
