clearml-iri-launch  \
    --project-name "AmSC/pipeline-iri-bridge"   --task-name "submit-iri-job"   --repo https://github.com/zhenghh04/alcf_clearml_deployment.git  \
    --branch main \
    --working-directory . \
    --facility alcf   \
    --system polaris   \
    --job-payload-json '{"name":"clearml-iri-job","executable":"/bin/bash","arguments":["-lc","echo hello from ClearML IRI bridge"],"directory":"/eagle/datascience/hzheng/","stdout_path":"/eagle/datascience/hzheng/iri.out","stderr_path":"/eagle/datascience/hzheng/iri.err","attributes":{"account":"AmSC_Demos","queue_name":"debug", "duration":300, "custom_attributes": {"filesystems":"home:eagle"}}}'   --queue crux-services   --tags-json '["iri-bridge"]'
