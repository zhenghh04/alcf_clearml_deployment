#!/bin/bash
# Activate the Cerebras PyTorch venv on cer-usn-01 / cer-usn-02.
# The venv is built once per ALCF release per the docs:
#   https://docs.alcf.anl.gov/ai-testbed/cerebras/customizing-environment/

# Cerebras user nodes need an outbound HTTP proxy for PyPI (clearml,
# clearml-agent install). amscclearml.alcf.anl.gov is on-fabric and must
# bypass the proxy.
export http_proxy=http://proxy.alcf.anl.gov:3128
export https_proxy=http://proxy.alcf.anl.gov:3128
export no_proxy=amscclearml.alcf.anl.gov,.alcf.anl.gov,localhost,127.0.0.1

# The release tag here matches the docs default. Bump when ALCF
# refreshes Cerebras software (R_2.10.0, R_2.11.0, ...).
source "${HOME}/R_2.9.0/venv_cerebras_pt/bin/activate"
