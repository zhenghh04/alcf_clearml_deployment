# Local Globus Transfer Setup

Use this when you want to transfer a file from your local machine into the remote filesystem before launching an IRI job.

## 1. Install Globus Connect Personal

Install **Globus Connect Personal** on your laptop or desktop. This is the usual way to expose a local machine to Globus Transfer.

Official install docs:

- https://docs.globus.org/globus-connect-personal/install/

## 2. Start the local endpoint

Launch Globus Connect Personal and sign in with your Globus account.

Keep the application running while transfers are active.

In Globus terminology, this gives you a local mapped collection for your machine.

## 3. Find the local collection or endpoint ID

If you use the Globus CLI:

```bash
globus login
globus endpoint local-id
```

You can also verify that the local collection is visible:

```bash
globus ls "$(globus endpoint local-id)":~/
```

CLI reference:

- https://docs.globus.org/cli/reference/endpoint_local-id/

## 4. Pick the source and destination

For the IRI examples in this folder, you will usually set:

- `SRC_ENDPOINT`: your local Globus Connect Personal collection
- `SRC_PATH`: the local file you want to upload
- `DST_ENDPOINT`: the remote collection that exposes the target filesystem
- `DST_PATH`: the final remote path where the file should land

Example:

```python
SRC_ENDPOINT = "YOUR_LOCAL_ENDPOINT_ID"
DST_ENDPOINT = "YOUR_REMOTE_ENDPOINT_ID"
SRC_PATH = "/Users/yourname/path/to/job.sh"
DST_PATH = "/home/hzheng/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/job.sh"
```

## 5. Run the example

For manual stage-in plus submit:

- [iri_stage_with_globus.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/iri_stage_with_globus.py)

For a pipeline that stages first and then submits the IRI job:

- [iri_stage_with_globus_pipeline.py](/Users/huihuo.zheng/Documents/Research/AmSC/clearml/alcf_clearml_deployment/examples/job_launching/iri/python/iri_stage_with_globus_pipeline.py)

## Notes

- For a local machine, use **Globus Connect Personal**, not Globus Connect Server.
- The local app must stay running during the transfer.
- The destination endpoint must already expose the remote filesystem you want to write to.
