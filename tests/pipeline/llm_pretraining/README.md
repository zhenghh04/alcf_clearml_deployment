# LLM Pretraining Pipeline

This pipeline is intended to:

1. Download a dataset on **crux** to `/eagle/AuroraGPT/datasets`.
2. Tokenize the dataset on **crux** (output stays under `/eagle/AuroraGPT/datasets`).
3. Transfer tokenized data from **crux** (`/eagle/AuroraGPT/datasets`) to **Aurora** (`/flare/AuroraGPT/`) using **Globus**.
4. Train the model on **Aurora** using **megatron-deepspeed**.

## Planned structure

- `pipeline.py`: ClearML pipeline driver (download + tokenize -> Globus transfer -> train).
- `tasks/`:
  - `download_dataset.py` (or `.sh`): dataset fetch on crux.
  - `tokenize.py` (or `.sh`): tokenization on crux.
  - `transfer_globus.py`: reuse the Globus transfer task from `tests/pipeline/multi_facilities/tasks/`.
  - `train_megatron.py` (or `.sh`): training launch on Aurora using megatron-deepspeed.

## Globus transfer

We will follow the same approach as the multi-facilities example:

- Reference implementation: `tests/pipeline/multi_facilities/tasks/transfer_globus.py`
- Wrapper example: `tests/pipeline/multi_facilities/tasks/globus_transfer.sh`

The transfer step will pass (or export) variables such as:

- `GLOBUS_SRC_ENDPOINT`
- `GLOBUS_DST_ENDPOINT`
- `GLOBUS_SRC_PATH=/eagle/AuroraGPT/datasets`
- `GLOBUS_DST_PATH=/flare/AuroraGPT/`
- `GLOBUS_RECURSIVE=1`

## Open items (to confirm before implementation)

- Dataset name(s), source URLs, and expected on-disk layout
- Tokenizer and preprocessing toolchain (e.g., Hugging Face tokenizer, Megatron preprocessing)
- Globus endpoint IDs for `/eagle` and `/flare`
- Megatron-deepspeed launch command and environment/module setup
- ClearML queues to use for crux vs Aurora

Once these are confirmed, I can implement the pipeline and task scripts.
