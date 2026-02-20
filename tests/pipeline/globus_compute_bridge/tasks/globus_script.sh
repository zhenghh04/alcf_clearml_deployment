#!/bin/bash
nvidia-smi
echo "Sleeping for 10 seconds to simulate a long-running task..."
python -c "import time; time.sleep(10)"
echo "Done sleeping, exiting now."