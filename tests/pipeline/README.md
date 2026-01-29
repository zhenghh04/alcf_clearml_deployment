# Pipeline tests

This folder contains ClearML pipeline examples. Pipelines can dispatch steps to different queues, which allows you to run components across multiple supercomputers (one queue per system).

## Important setup for running pipeline jobs



## Run on multiple queues (multiple systems)
To run pipeline steps on multiple queues:

1) Create queues for different systems on the ClearML dashboard
2) Start agents on each system, each listening to its own queue associated to the system
3) Assign `execution_queue` per step.

### Example (PipelineDecorator)
```python
@PipelineDecorator.component(execution_queue="sirius-login")
def step_sirius(...):
    ...

@PipelineDecorator.component(execution_queue="crux-login")
def step_crux(...):
    ...

@PipelineDecorator.component(execution_queue="polaris-login")
def step_polaris(...):
    ...
```

### Example (PipelineController)
```python
pipe.add_step(
    name="step_sirius",
    base_task_project="AmSC",
    base_task_name="sirius-step",
    execution_queue="sirius-login",
)
pipe.add_step(
    name="step_crux",
    base_task_project="AmSC",
    base_task_name="crux-step",
    execution_queue="crux-login",
    parents=["step_sirius"],
)

pipe.start(queue="crux-login")
```

**IMPORTANT**: By default the pipeline controller runs on the `services-agent` queue (on the ClearML server), which you typically do not control. That agent often runs in Docker and may do extra environment setup. To avoid running the controller on `services-agent`, run the controller on a user defined queue:

```python
pipe.start(queue="crux-login")
```

## Notes
- Queues must exist before agents attach. Create a queue by enqueueing a task to it.
- If a step hangs after “Launching step …”, it usually means no agent is listening on that queue.
