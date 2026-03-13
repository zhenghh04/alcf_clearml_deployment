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


def _get_dataset_by_id(dataset_id: str, include_archived: bool = True) -> Any:
    from clearml import Dataset

    return Dataset.get(dataset_id=dataset_id, include_archived=include_archived)


def _get_model_by_id(model_id: str) -> Any:
    from clearml import Model

    return Model(model_id=model_id)


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
    model = _get_model_by_id(model_id=model_id)
    return _summarize_model(model)


@mcp.tool
def download_model(
    model_id: str,
    target_dir: str = "",
    extract_archive: bool = True,
    force_download: bool = False,
) -> Dict[str, Any]:
    """Download a registered model locally."""
    model = _get_model_by_id(model_id=model_id)
    local_path = model.get_local_copy(
        extract_archive=extract_archive,
        raise_on_error=True,
        force_download=force_download,
    )
    copied_path = _copy_to_target(local_path, target_dir) if target_dir else None
    return {
        **_summarize_model(model),
        "local_path": local_path,
        "copied_path": copied_path,
        "extract_archive": extract_archive,
    }


@mcp.tool
def register_model(
    project_name: str,
    model_name: str,
    weights_path: str = "",
    register_uri: str = "",
    tags: str = "",
    comment: str = "",
    framework: str = "",
    config_text: str = "",
    output_uri: str = "",
    publish: bool = False,
    task_name: str = "",
) -> Dict[str, Any]:
    """
    Register a model in ClearML from a local weights file or an existing URI.

    Exactly one of weights_path or register_uri must be provided.
    """
    from clearml import OutputModel, Task

    if bool(weights_path) == bool(register_uri):
        raise ValueError("Provide exactly one of weights_path or register_uri")

    task = Task.create(
        project_name=project_name,
        task_name=task_name or f"register-model::{model_name}",
        task_type="training",
    )
    if output_uri:
        task.output_uri = output_uri

    output_model = OutputModel(
        task=task,
        name=model_name,
        tags=_split_csv(tags) or None,
        comment=comment or None,
        framework=framework or None,
        config_text=config_text or None,
    )

    if weights_path:
        output_model.update_weights(
            weights_filename=weights_path,
            upload_uri=output_uri or None,
            auto_delete_file=False,
            async_enable=False,
        )
    else:
        output_model.update_weights(
            register_uri=register_uri,
            async_enable=False,
        )

    if publish:
        output_model.publish()

    try:
        task.close()
    except Exception:
        pass
    try:
        task.mark_completed()
    except Exception:
        pass

    model = _get_model_by_id(output_model.id)
    result = _summarize_model(model)
    result["published"] = publish or result.get("published")
    result["task_id"] = task.id
    return result


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
def download_dataset(
    dataset_id: str,
    target_dir: str = "",
    include_archived: bool = True,
    writable_copy: bool = True,
    overwrite: bool = False,
    use_soft_links: bool = False,
    part: int = -1,
    num_parts: int = -1,
) -> Dict[str, Any]:
    """Download a dataset locally, either as a cached read-only copy or a writable target copy."""
    dataset = _get_dataset_by_id(dataset_id=dataset_id, include_archived=include_archived)
    part_value = None if part < 0 else part
    num_parts_value = None if num_parts < 0 else num_parts

    if writable_copy:
        if not target_dir:
            raise ValueError("target_dir is required when writable_copy=True")
        local_path = dataset.get_mutable_local_copy(
            target_folder=target_dir,
            overwrite=overwrite,
            part=part_value,
            num_parts=num_parts_value,
        )
    else:
        local_path = dataset.get_local_copy(
            use_soft_links=use_soft_links,
            part=part_value,
            num_parts=num_parts_value,
        )
        if target_dir:
            local_path = _copy_to_target(local_path, target_dir)

    return {
        "dataset": _summarize_dataset(get_dataset(dataset_id=dataset_id, include_archived=include_archived)["raw"]),
        "local_path": local_path,
        "writable_copy": writable_copy,
        "part": part_value,
        "num_parts": num_parts_value,
    }


@mcp.tool
def upload_dataset(
    dataset_project: str,
    dataset_name: str,
    local_path: str = "",
    external_urls: str = "",
    dataset_version: str = "",
    parent_dataset_ids: str = "",
    tags: str = "",
    description: str = "",
    output_uri: str = "",
    dataset_path: str = "",
    use_sync_folder: bool = True,
    finalize: bool = True,
    auto_upload: bool = True,
    chunk_size_mb: int = 0,
) -> Dict[str, Any]:
    """
    Create and upload a dataset from a local folder/file and/or external URLs.

    At least one of local_path or external_urls must be provided.
    """
    from clearml import Dataset

    if not local_path and not external_urls:
        raise ValueError("At least one of local_path or external_urls must be provided")

    dataset = Dataset.create(
        dataset_name=dataset_name,
        dataset_project=dataset_project,
        dataset_tags=_split_csv(tags) or None,
        parent_datasets=_split_csv(parent_dataset_ids) or None,
        dataset_version=dataset_version or None,
        output_uri=output_uri or None,
        description=description or None,
    )

    if local_path:
        if use_sync_folder and os.path.isdir(local_path):
            dataset.sync_folder(
                local_path=local_path,
                dataset_path=dataset_path or None,
                verbose=False,
            )
        else:
            dataset.add_files(
                path=local_path,
                dataset_path=dataset_path or None,
                recursive=True,
                verbose=False,
            )

    if external_urls:
        dataset.add_external_files(
            source_url=_split_csv(external_urls),
            dataset_path=dataset_path or None,
            recursive=True,
            verbose=False,
        )

    if auto_upload:
        upload_kwargs: Dict[str, Any] = {
            "show_progress": False,
            "verbose": False,
            "output_url": output_uri or None,
        }
        if chunk_size_mb > 0:
            upload_kwargs["chunk_size"] = chunk_size_mb
        dataset.upload(**upload_kwargs)

    if finalize:
        dataset.finalize(verbose=False, auto_upload=auto_upload)

    return {
        "id": dataset.id,
        "name": dataset.name,
        "project": dataset.project,
        "version": dataset.version,
        "tags": dataset.tags,
        "created": True,
        "local_path": local_path or None,
        "external_urls": _split_csv(external_urls),
        "finalized": finalize,
        "auto_uploaded": auto_upload,
        "output_uri": output_uri or dataset.get_default_storage(),
    }


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
