# ResNet50 experiment tracking conversion examples (W&B / MLflow -> ClearML)

This folder shows side-by-side, minimal ResNet50 training examples using:
- Weights & Biases (W&B)
- MLflow
- ClearML

The goal is to show what changes when you migrate **experiment tracking** to ClearML.

## Files

- `resnet50_wandb.py`: W&B tracking example
- `resnet50_mlflow.py`: MLflow tracking example
- `resnet50_clearml.py`: ClearML tracking example
- `requirements.txt`: pinned example versions (adjust if needed)

## Example versions

These are **example pinned versions** used for this conversion sample:
- `wandb==0.16.6`
- `mlflow==2.10.2`
- `clearml==2.0.6`
- `torch==2.2.2`
- `torchvision==0.17.2`

If your environment already has different versions, keep them and just run the scripts. You can verify your installed versions with:

```
pip show wandb mlflow clearml torch torchvision
```

## Quickstart

Create a clean env (optional):

```
python -m venv .venv
source .venv/bin/activate
pip install -r examples/experiment_tracking/resnet50_conversion/requirements.txt
```

### 1) W&B example

```
python examples/experiment_tracking/resnet50_conversion/resnet50_wandb.py \
  --epochs 1 --batch-size 32
```

### 2) MLflow example

```
python examples/experiment_tracking/resnet50_conversion/resnet50_mlflow.py \
  --epochs 1 --batch-size 32
```

### 3) ClearML example

```
python examples/experiment_tracking/resnet50_conversion/resnet50_clearml.py \
  --epochs 1 --batch-size 32
```

## Conversion cheat sheet

### W&B -> ClearML

**W&B**

```python
import wandb
run = wandb.init(project="demo", config=vars(args))
wandb.log({"train/loss": loss, "train/acc": acc, "epoch": epoch})
run.finish()
```

**ClearML**

```python
from clearml import Task

task = Task.init(project_name="demo", task_name="resnet50")
logger = task.get_logger()
logger.report_scalar("train", "loss", loss, iteration=step)
logger.report_scalar("train", "acc", acc, iteration=step)
```

### MLflow -> ClearML

**MLflow**

```python
import mlflow
mlflow.start_run()
mlflow.log_params(vars(args))
mlflow.log_metric("train_loss", loss, step=step)
mlflow.end_run()
```

**ClearML**

```python
from clearml import Task

task = Task.init(project_name="demo", task_name="resnet50")
task.connect(vars(args))
logger = task.get_logger()
logger.report_scalar("train", "loss", loss, iteration=step)
```

## Notes

- These scripts use `torchvision.datasets.FakeData` so they run without downloading datasets.
- To use real data, replace `FakeData` with your dataset (e.g., CIFAR10 or ImageNet).
- For ClearML, ensure your `clearml.conf` is configured (server URL, credentials).
