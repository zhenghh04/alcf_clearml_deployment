export https_proxy=http://proxy.alcf.anl.gov:3128
export http_proxy=http://proxy.alcf.anl.gov:3128
module load frameworks
source $HOME//clearml/alcf_clearml_deployment/clients/clearml_agent_setup/envs/clearml/bin/activate

# Persistent TMPDIR — avoids /tmp purge killing agent temp config
export TMPDIR="$HOME/tmp"
mkdir -p "$TMPDIR"
