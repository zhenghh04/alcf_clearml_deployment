export https_proxy=http://proxy.alcf.anl.gov:3128
export http_proxy=http://proxy.alcf.anl.gov:3128
module load frameworks
source $HOME//clearml/alcf_clearml_evaluation/clients/aurora/envs/clearml/bin/activate
export PATH=/home/hzheng/.local/aurora/frameworks/2025.2.0/bin:$PATH
