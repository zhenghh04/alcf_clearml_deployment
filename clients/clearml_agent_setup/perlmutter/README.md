# Perlmutter ClearML client (draft)

This folder contains an initial draft setup for running a ClearML client environment on NERSC Perlmutter.

## 1. Create the environment
```bash
bash clients/clearml_agent_setup/perlmutter/setup_env.sh
```

## 2. Activate the environment
```bash
source clients/clearml_agent_setup/perlmutter/conda.sh
```

## Notes
- `setup_env.sh` defaults to `clients/clearml_agent_setup/perlmutter/envs/clearml`.
- Override env path with `PERLMUTTER_CLEARML_VENV=/path/to/venv`.
- Override python with `PERLMUTTER_PYTHON_BIN=/path/to/python`.
- This is a bootstrap draft and may require module/account adjustments.
