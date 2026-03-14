# ClearML Query MCP Server

This folder contains a read-only MCP server for querying a ClearML deployment.

Implemented tools:

- `server_config`
- `list_models`
- `get_model`
- `download_model`
- `register_model`
- `list_datasets`
- `get_dataset`
- `download_dataset`
- `upload_dataset`
- `search_tasks`
- `get_task`
- `list_task_artifacts`
- `read_task_artifact`
- `download_task_artifact`
- `list_queues`
- `list_agents`

The server uses the same ClearML configuration as other repo tools:

- `CLEARML_API_HOST`
- `CLEARML_WEB_HOST`
- `CLEARML_FILES_HOST`
- `CLEARML_ACCESS_KEY`
- `CLEARML_SECRET_KEY`

or any working ClearML SDK config on the machine.

## Tools

This section describes each MCP tool, its main parameters, and the shape of the returned data.

### `server_config`

Returns the ClearML endpoint configuration visible to the MCP server.

Returns:

- `api_host`
- `web_host`
- `files_host`
- `has_access_key`
- `has_secret_key`

Use this first if you need to verify which ClearML deployment the server is pointed at.

### `list_models`

Lists registered ClearML models.

Main parameters:

- `project_name`: filter by project name
- `model_name`: filter by model name
- `tags`: comma-separated model tags
- `only_published`: return only published models
- `include_archived`: include archived models
- `max_results`: cap result count

Returns one summary object per model with fields such as:

- `id`
- `name`
- `project`
- `comment`
- `tags`
- `uri`
- `task`
- `published`
- `framework`
- `raw`

Example use cases:

- Find all models for one project
- Find published models only
- Inspect storage URIs for model artifacts

### `get_model`

Fetches one registered model by model ID.

Main parameters:

- `model_id`

Returns the same summary structure as `list_models`, but for a single model.

### `download_model`

Downloads a registered model locally by model ID.

Main parameters:

- `model_id`
- `target_dir`
- `extract_archive`
- `force_download`

Behavior:

- Retrieves the model weights or package through ClearML storage helpers
- If `target_dir` is provided, copies the downloaded model there
- Supports extracting packaged models when `extract_archive=True`

Returns:

- All model summary fields from `get_model`
- `local_path`
- `copied_path`
- `extract_archive`

### `register_model`

Registers a new model in ClearML from either a local weights file or an already uploaded URI.

Main parameters:

- `project_name`
- `model_name`
- `weights_path`: local file to upload
- `register_uri`: existing model URI to register without uploading
- `tags`
- `comment`
- `framework`
- `config_text`
- `output_uri`
- `publish`
- `task_name`

Behavior:

- Creates a lightweight backing task in ClearML
- Creates an `OutputModel`
- Uploads model weights from `weights_path`, or registers `register_uri`
- Optionally publishes the model

Returns:

- Model summary fields
- `task_id`: the backing registration task ID

Notes:

- Provide exactly one of `weights_path` or `register_uri`
- `output_uri` controls where uploaded weights are stored when using `weights_path`

### `list_datasets`

Lists ClearML datasets.

Main parameters:

- `dataset_project`: filter by dataset project
- `partial_name`: partial dataset name match
- `tags`: comma-separated dataset tags
- `ids`: comma-separated dataset IDs
- `only_completed`: only return completed datasets
- `include_archived`: include archived datasets

Returns one summary object per dataset with fields such as:

- `id`
- `name`
- `project`
- `version`
- `tags`
- `status`
- `created`
- `last_update`
- `task`
- `raw`

### `get_dataset`

Fetches one dataset record by dataset ID.

Main parameters:

- `dataset_id`
- `include_archived`

Returns the same summary structure as `list_datasets`, but for a single dataset.

### `download_dataset`

Downloads a dataset locally by dataset ID.

Main parameters:

- `dataset_id`
- `target_dir`: optional target directory
- `include_archived`
- `writable_copy`: if `True`, create a writable copy in `target_dir`
- `overwrite`: only used with `writable_copy=True`
- `use_soft_links`: only used for read-only cached copies
- `part`
- `num_parts`

Behavior:

- If `writable_copy=True`, materializes a writable dataset copy into `target_dir`
- If `writable_copy=False`, fetches the cached read-only dataset copy
- If `target_dir` is supplied with `writable_copy=False`, copies the cached dataset there
- Supports partial dataset retrieval with `part` / `num_parts`

Returns:

- `dataset`
- `local_path`
- `writable_copy`
- `part`
- `num_parts`

### `upload_dataset`

Creates and uploads a new dataset from a local path and/or external URLs.

Main parameters:

- `dataset_project`
- `dataset_name`
- `local_path`: local file or folder to add
- `external_urls`: comma-separated external URLs such as `s3://...`, `gs://...`, `file://...`, `https://...`
- `dataset_version`
- `parent_dataset_ids`: comma-separated parent dataset IDs
- `tags`: comma-separated dataset tags
- `description`
- `output_uri`
- `dataset_path`: target path inside the dataset
- `use_sync_folder`: use `sync_folder` for local directories
- `finalize`
- `auto_upload`
- `chunk_size_mb`

Behavior:

- Creates a new dataset task
- Adds local files/folders if `local_path` is provided
- Adds linked external files if `external_urls` is provided
- Uploads pending files when `auto_upload=True`
- Finalizes the dataset when `finalize=True`

Returns:

- `id`
- `name`
- `project`
- `version`
- `tags`
- `created`
- `local_path`
- `external_urls`
- `finalized`
- `auto_uploaded`
- `output_uri`

### `search_tasks`

Searches ClearML tasks using common filters.

Main parameters:

- `project_name`
- `task_name`
- `tags`: comma-separated task tags
- `task_ids`: comma-separated task IDs
- `status`: comma-separated statuses such as `created,queued,in_progress,completed,failed,stopped`
- `task_types`: comma-separated task types such as `training,data_processing,controller,testing`
- `system_tags`: comma-separated system tags such as `pipeline`
- `allow_archived`
- `limit`

Returns one summary object per task with fields such as:

- `id`
- `name`
- `project`
- `type`
- `status`
- `user`
- `tags`
- `system_tags`
- `last_update`
- `last_iteration`
- `raw`

Typical uses:

- Find non-complete jobs
- Find pipeline controllers
- Look up recent failed tasks

### `get_task`

Fetches one ClearML task by task ID.

Main parameters:

- `task_id`
- `allow_archived`

Returns the same summary structure as `search_tasks`, including the raw task payload in `raw`.

Use `raw` when you need queue IDs, artifacts, script info, status reasons, or full runtime metadata.

### `list_task_artifacts`

Lists artifacts attached to one task.

Main parameters:

- `task_id`
- `allow_archived`

Returns one summary object per artifact with fields such as:

- `name`
- `type`
- `mode`
- `url`
- `size`
- `hash`
- `timestamp`
- `metadata`
- `preview`

This is the best starting point before downloading or reading an artifact.

### `read_task_artifact`

Reads a task artifact and attempts to deserialize it using the ClearML SDK.

Main parameters:

- `task_id`
- `artifact_name`
- `allow_archived`
- `force_download`
- `max_text_chars`

Behavior:

- For structured/text artifacts, returns deserialized `content`
- For text content, truncates to `max_text_chars`
- For binary or unsupported formats, returns a local cached path instead of inline content

Returned fields include:

- All artifact summary fields from `list_task_artifacts`
- `python_type`
- `content`
- `local_path`
- `truncated`

Useful for:

- Reading JSON/YAML/string artifacts inline
- Inspecting artifact previews
- Getting a cached local path for manual analysis

### `download_task_artifact`

Downloads a task artifact to the local ClearML cache and optionally copies it into a target directory.

Main parameters:

- `task_id`
- `artifact_name`
- `target_dir`
- `allow_archived`
- `extract_archive`
- `force_download`

Behavior:

- Downloads the artifact through ClearML storage helpers
- If `extract_archive=True` and the artifact is an archive, returns the extracted directory
- If `target_dir` is provided, copies the downloaded file or extracted directory there

Returns:

- All artifact summary fields from `list_task_artifacts`
- `local_path`
- `copied_path`
- `extract_archive`

This is the tool to use before external analysis scripts, notebook inspection, or shell-based analysis.

### `list_queues`

Lists ClearML execution queues through the low-level API client.

Main parameters:

- `only_fields`: comma-separated API fields to request, for example `id,name,entries,metadata`

Returns one summary object per queue with fields such as:

- `id`
- `name`
- `user`
- `company`
- `created`
- `tags`
- `entries`
- `metadata`
- `raw`

Common uses:

- See queue names and IDs
- Check queued task entries
- Inspect queue metadata

### `list_agents`

Lists ClearML agents/workers through the low-level API client.

Main parameters:

- `only_fields`: comma-separated API fields to request when supported by the backend

Returns one summary object per worker with fields such as:

- `id`
- `name`
- `ip`
- `host`
- `user`
- `task`
- `queues`
- `last_activity_time`
- `register_time`
- `raw`

Notes:

- The implementation falls back to a full worker query if the backend does not support `only_fields`
- This is useful for checking which queues have active consumers

## Example Queries

Examples below use tool names and parameter payloads conceptually; invoke them through your MCP client or Codex tool layer.

List recent failed pipeline tasks:

```json
{
  "tool": "search_tasks",
  "arguments": {
    "status": "failed",
    "system_tags": "pipeline",
    "limit": 20
  }
}
```

List artifacts on one task:

```json
{
  "tool": "list_task_artifacts",
  "arguments": {
    "task_id": "14ca68ec108c443697a251987344d725"
  }
}
```

Download a registered model:

```json
{
  "tool": "download_model",
  "arguments": {
    "model_id": "1ba1823073374194ac6f15c28666527d",
    "target_dir": "/tmp/models"
  }
}
```

Register a model from a local file:

```json
{
  "tool": "register_model",
  "arguments": {
    "project_name": "AmSC",
    "model_name": "best-resnet50-cifar10",
    "weights_path": "/tmp/best_resnet50_cifar10.pth",
    "framework": "PyTorch",
    "publish": false
  }
}
```

Read a JSON artifact inline:

```json
{
  "tool": "read_task_artifact",
  "arguments": {
    "task_id": "14ca68ec108c443697a251987344d725",
    "artifact_name": "state"
  }
}
```

Download an artifact into a working directory:

```json
{
  "tool": "download_task_artifact",
  "arguments": {
    "task_id": "14ca68ec108c443697a251987344d725",
    "artifact_name": "state",
    "target_dir": "/tmp/clearml_artifacts"
  }
}
```

Download a dataset into a writable local folder:

```json
{
  "tool": "download_dataset",
  "arguments": {
    "dataset_id": "8d728bc930f243849fec4303808fcaeb",
    "target_dir": "/tmp/allenai-c4",
    "writable_copy": true,
    "overwrite": true
  }
}
```

Create and upload a dataset from a local folder:

```json
{
  "tool": "upload_dataset",
  "arguments": {
    "dataset_project": "AmSC/.datasets/demo",
    "dataset_name": "demo-dataset",
    "local_path": "/tmp/my_data",
    "dataset_version": "1.0.0",
    "finalize": true,
    "auto_upload": true
  }
}
```

## Run

From the repo root:

```bash
python3 -m alcf_clearml_deployment.server.mcp.clearml_query_server
```

For stdio MCP transport explicitly:

```bash
python3 -m alcf_clearml_deployment.server.mcp.clearml_query_server stdio
```

From inside `alcf_clearml_deployment/` you can also run:

```bash
python3 -m server.mcp.clearml_query_server
```

For an HTTP transport:

```bash
python3 -m server.mcp.clearml_query_server streamable-http --host 0.0.0.0 --port 8005
```

## Register with Codex

From the repo root, register the MCP server with Codex:

```bash
codex mcp add clearml-query -- python3 /Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/server/mcp/clearml_query_server.py
```

If you prefer the module entry point, run:

```bash
codex mcp add clearml-query -- python3 -m alcf_clearml_deployment.server.mcp.clearml_query_server
```

Verify the registration:

```bash
codex mcp list
```


## Notes

- Query tools are read-only, but artifact download helpers can fetch cached copies of task artifacts.
- Queue and agent queries use the low-level ClearML `APIClient`.
- Model, dataset, and task queries use the public ClearML SDK.
