import argparse
import os
import shutil
from typing import Any, Dict, List, Optional, Sequence

from fastmcp import FastMCP


mcp = FastMCP(
    name="ClearML Query MCP",
    instructions=(
        "Read-only ClearML query server for models, datasets, tasks, queues, and agents. "
        "It uses the ClearML SDK configuration from the current environment."
    ),
)


def _split_csv(raw: str) -> List[str]:
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def _client() -> Any:
    from clearml.backend_api.session.client import APIClient

    return APIClient()


def _to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    for attr in ("to_dict", "as_dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                result = fn()
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
    data: Dict[str, Any] = {}
    for key, value in vars(obj).items():
        if key.startswith("_"):
            continue
        if callable(value):
            continue
        data[key] = value
    return data


def _pick(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _summarize_model(model: Any) -> Dict[str, Any]:
    data = _to_dict(model)
    return {
        "id": _pick(data, "id", "model_id") or getattr(model, "id", None),
        "name": _pick(data, "name") or getattr(model, "name", None),
        "project": _pick(data, "project", "project_name") or getattr(model, "project", None),
        "comment": _pick(data, "comment") or getattr(model, "comment", None),
        "tags": _pick(data, "tags", "system_tags") or getattr(model, "tags", None),
        "uri": _pick(data, "uri", "url") or getattr(model, "url", None),
        "task": _pick(data, "task"),
        "published": _pick(data, "published"),
        "framework": _pick(data, "framework"),
        "raw": data,
    }


def _summarize_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _pick(dataset, "id"),
        "name": _pick(dataset, "name"),
        "project": _pick(dataset, "project", "dataset_project"),
        "version": _pick(dataset, "version"),
        "tags": _pick(dataset, "tags"),
        "status": _pick(dataset, "status"),
        "created": _pick(dataset, "created"),
        "last_update": _pick(dataset, "last_update"),
        "task": _pick(dataset, "task"),
        "raw": dataset,
    }


def _summarize_task(task: Any) -> Dict[str, Any]:
    data = _to_dict(getattr(task, "data", None))
    if not data:
        data = _to_dict(task)
    return {
        "id": _pick(data, "id") or getattr(task, "id", None),
        "name": _pick(data, "name") or getattr(task, "name", None),
        "project": _pick(data, "project") or getattr(task, "project", None),
        "type": _pick(data, "type", "task_type"),
        "status": _pick(data, "status"),
        "user": _pick(data, "user"),
        "tags": _pick(data, "tags"),
        "system_tags": _pick(data, "system_tags"),
        "last_update": _pick(data, "last_update"),
        "last_iteration": _pick(data, "last_iteration"),
        "raw": data,
    }


def _summarize_artifact(artifact: Any) -> Dict[str, Any]:
    return {
        "name": getattr(artifact, "name", None),
        "type": getattr(artifact, "type", None),
        "mode": getattr(artifact, "mode", None),
        "url": getattr(artifact, "url", None),
        "size": getattr(artifact, "size", None),
        "hash": getattr(artifact, "hash", None),
        "timestamp": (
            getattr(artifact, "timestamp", None).isoformat()
            if getattr(artifact, "timestamp", None) is not None
            else None
        ),
        "metadata": getattr(artifact, "metadata", None),
        "preview": getattr(artifact, "preview", None),
    }


def _summarize_queue(queue: Any) -> Dict[str, Any]:
    data = _to_dict(queue)
    return {
        "id": _pick(data, "id"),
        "name": _pick(data, "name"),
        "user": _pick(data, "user"),
        "company": _pick(data, "company"),
        "created": _pick(data, "created"),
        "tags": _pick(data, "tags", "system_tags"),
        "entries": _pick(data, "entries"),
        "metadata": _pick(data, "metadata"),
        "raw": data,
    }


def _summarize_worker(worker: Any) -> Dict[str, Any]:
    data = _to_dict(worker)
    queue_ids = []
    queues = data.get("queues") or []
    for entry in queues:
        if isinstance(entry, dict):
            queue_ids.append(entry.get("id") or entry.get("queue"))
        else:
            queue_ids.append(getattr(entry, "id", None) or getattr(entry, "queue", None))
    return {
        "id": _pick(data, "id"),
        "name": _pick(data, "name"),
        "ip": _pick(data, "ip"),
        "host": _pick(data, "host"),
        "user": _pick(data, "user"),
        "task": _pick(data, "task"),
        "queues": [q for q in queue_ids if q],
        "last_activity_time": _pick(data, "last_activity_time", "last_activity"),
        "register_time": _pick(data, "register_time"),
        "raw": data,
    }


def _task_filter(
    status: Optional[Sequence[str]] = None,
    task_types: Optional[Sequence[str]] = None,
    system_tags: Optional[Sequence[str]] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    task_filter: Dict[str, Any] = {"page_size": max(1, min(limit, 200))}
    if status:
        task_filter["status"] = list(status)
    if task_types:
        task_filter["type"] = list(task_types)
    if system_tags:
        task_filter["system_tags"] = list(system_tags)
    task_filter["order_by"] = ["-last_update"]
    return task_filter


def _get_task_by_id(task_id: str, allow_archived: bool = True) -> Any:
    from clearml import Task

    task = Task.get_task(task_id=task_id, allow_archived=allow_archived)
    if not task:
        raise ValueError(f"Task not found: {task_id}")
    return task


def _get_task_artifact(task_id: str, artifact_name: str, allow_archived: bool = True) -> Any:
    task = _get_task_by_id(task_id=task_id, allow_archived=allow_archived)
    artifact = task.artifacts.get(artifact_name)
    if not artifact:
        raise ValueError(f"Artifact '{artifact_name}' not found on task {task_id}")
    return artifact


def _copy_to_target(path: str, target_dir: str) -> str:
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, os.path.basename(path.rstrip(os.sep)))
    if os.path.isdir(path):
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        shutil.copytree(path, target_path)
    else:
        shutil.copy2(path, target_path)
    return target_path


@mcp.tool
def server_config() -> Dict[str, Any]:
    """Return the ClearML endpoint configuration visible to this MCP server."""
    return {
        "api_host": os.getenv("CLEARML_API_HOST"),
        "web_host": os.getenv("CLEARML_WEB_HOST"),
        "files_host": os.getenv("CLEARML_FILES_HOST"),
        "has_access_key": bool(os.getenv("CLEARML_ACCESS_KEY")),
        "has_secret_key": bool(os.getenv("CLEARML_SECRET_KEY")),
    }


@mcp.tool
def list_models(
    project_name: str = "",
    model_name: str = "",
    tags: str = "",
    only_published: bool = False,
    include_archived: bool = False,
    max_results: int = 50,
) -> List[Dict[str, Any]]:
    """List registered ClearML models."""
    from clearml import Model

    models = Model.query_models(
        project_name=project_name or None,
        model_name=model_name or None,
        tags=_split_csv(tags) or None,
        only_published=only_published,
        include_archived=include_archived,
        max_results=max(1, min(max_results, 200)),
    )
    return [_summarize_model(model) for model in models]


@mcp.tool
def get_model(model_id: str) -> Dict[str, Any]:
    """Get one registered ClearML model by id."""
    from clearml import Model

    model = Model(model_id=model_id)
    return _summarize_model(model)


@mcp.tool
def list_datasets(
    dataset_project: str = "",
    partial_name: str = "",
    tags: str = "",
    ids: str = "",
    only_completed: bool = True,
    include_archived: bool = True,
) -> List[Dict[str, Any]]:
    """List dataset metadata from ClearML."""
    from clearml import Dataset

    datasets = Dataset.list_datasets(
        dataset_project=dataset_project or None,
        partial_name=partial_name or None,
        tags=_split_csv(tags) or None,
        ids=_split_csv(ids) or None,
        only_completed=only_completed,
        include_archived=include_archived,
    )
    return [_summarize_dataset(dataset) for dataset in datasets]


@mcp.tool
def get_dataset(dataset_id: str, include_archived: bool = True) -> Dict[str, Any]:
    """Get one dataset record by id."""
    from clearml import Dataset

    datasets = Dataset.list_datasets(
        ids=[dataset_id],
        only_completed=False,
        include_archived=include_archived,
    )
    if not datasets:
        raise ValueError(f"Dataset not found: {dataset_id}")
    return _summarize_dataset(datasets[0])


@mcp.tool
def search_tasks(
    project_name: str = "",
    task_name: str = "",
    tags: str = "",
    task_ids: str = "",
    status: str = "",
    task_types: str = "",
    system_tags: str = "",
    allow_archived: bool = True,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Search ClearML tasks."""
    from clearml import Task

    tasks = Task.get_tasks(
        task_ids=_split_csv(task_ids) or None,
        project_name=project_name or None,
        task_name=task_name or None,
        tags=_split_csv(tags) or None,
        allow_archived=allow_archived,
        task_filter=_task_filter(
            status=_split_csv(status) or None,
            task_types=_split_csv(task_types) or None,
            system_tags=_split_csv(system_tags) or None,
            limit=limit,
        ),
    )
    return [_summarize_task(task) for task in tasks[: max(1, min(limit, 200))]]


@mcp.tool
def get_task(task_id: str, allow_archived: bool = True) -> Dict[str, Any]:
    """Get one ClearML task by id."""
    task = _get_task_by_id(task_id=task_id, allow_archived=allow_archived)
    return _summarize_task(task)


@mcp.tool
def list_task_artifacts(task_id: str, allow_archived: bool = True) -> List[Dict[str, Any]]:
    """List artifacts attached to one ClearML task."""
    task = _get_task_by_id(task_id=task_id, allow_archived=allow_archived)
    return [_summarize_artifact(artifact) for artifact in task.artifacts.values()]


@mcp.tool
def read_task_artifact(
    task_id: str,
    artifact_name: str,
    allow_archived: bool = True,
    force_download: bool = False,
    max_text_chars: int = 20000,
) -> Dict[str, Any]:
    """
    Read and deserialize a task artifact when possible.

    For structured/text artifacts this returns the content directly.
    For binary or unsupported artifacts this returns a local cached path.
    """
    artifact = _get_task_artifact(
        task_id=task_id,
        artifact_name=artifact_name,
        allow_archived=allow_archived,
    )
    value = artifact.get(force_download=force_download)
    result = _summarize_artifact(artifact)
    result["python_type"] = type(value).__name__

    if isinstance(value, (dict, list, int, float, bool)) or value is None:
        result["content"] = value
        return result
    if isinstance(value, str):
        result["content"] = value[: max(1, max_text_chars)]
        result["truncated"] = len(value) > max(1, max_text_chars)
        return result

    local_path = str(value)
    result["local_path"] = local_path
    result["content"] = None
    return result


@mcp.tool
def download_task_artifact(
    task_id: str,
    artifact_name: str,
    target_dir: str = "",
    allow_archived: bool = True,
    extract_archive: bool = True,
    force_download: bool = False,
) -> Dict[str, Any]:
    """Download one task artifact and optionally copy it into a target directory."""
    artifact = _get_task_artifact(
        task_id=task_id,
        artifact_name=artifact_name,
        allow_archived=allow_archived,
    )
    local_path = artifact.get_local_copy(
        extract_archive=extract_archive,
        raise_on_error=True,
        force_download=force_download,
    )
    copied_path = ""
    if target_dir:
        copied_path = _copy_to_target(local_path, target_dir)
    return {
        **_summarize_artifact(artifact),
        "local_path": local_path,
        "copied_path": copied_path or None,
        "extract_archive": extract_archive,
    }


@mcp.tool
def list_queues(only_fields: str = "id,name,user,tags,system_tags,created") -> List[Dict[str, Any]]:
    """List ClearML queues through the backend API client."""
    client = _client()
    fields = _split_csv(only_fields) or None
    queues = client.queues.get_all(only_fields=fields)
    return [_summarize_queue(queue) for queue in queues]


@mcp.tool
def list_agents(
    only_fields: str = "id,name,ip,host,user,task,queues,last_activity_time,register_time"
) -> List[Dict[str, Any]]:
    """List ClearML agents/workers through the backend API client."""
    client = _client()
    fields = _split_csv(only_fields) or None
    try:
        workers = client.workers.get_all(only_fields=fields)
    except TypeError:
        workers = client.workers.get_all()
    return [_summarize_worker(worker) for worker in workers]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ClearML query MCP server.")
    parser.add_argument(
        "transport",
        nargs="?",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport to use.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP-based transports.")
    parser.add_argument("--port", type=int, default=8005, help="Port for HTTP-based transports.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    run_kwargs: Dict[str, Any] = {}
    if args.transport != "stdio":
        run_kwargs["host"] = args.host
        run_kwargs["port"] = args.port
    mcp.run(transport=args.transport, **run_kwargs)


if __name__ == "__main__":
    main()
