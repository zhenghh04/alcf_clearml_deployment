#!/usr/bin/env python
import time
import os
print(time.time())
print(f"start running job {os.environ['PBS_JOBID']}")
print(time.time())
