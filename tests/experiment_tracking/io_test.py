from __future__ import print_function

import os
import time
from clearml import Task, Logger


def _env_int(name, default):
    value = os.environ.get(name)
    return int(value) if value is not None else default


def _env_str(name, default):
    return os.environ.get(name, default)


def _write_test(path, total_bytes, chunk_bytes):
    logger = Logger.current_logger()
    written = 0
    start = time.time()
    with open(path, "wb") as f:
        while written < total_bytes:
            to_write = min(chunk_bytes, total_bytes - written)
            f.write(b"\0" * to_write)
            written += to_write
            if written % (256 * 1024 * 1024) == 0 or written == total_bytes:
                elapsed = max(time.time() - start, 1e-9)
                mb_s = (written / (1024 * 1024)) / elapsed
                logger.report_scalar("io_write", "mb_s", iteration=written, value=mb_s)
    elapsed = max(time.time() - start, 1e-9)
    return elapsed


def _read_test(path, chunk_bytes):
    logger = Logger.current_logger()
    read_bytes = 0
    start = time.time()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk_bytes)
            if not data:
                break
            read_bytes += len(data)
            if read_bytes % (256 * 1024 * 1024) == 0 or read_bytes == os.path.getsize(path):
                elapsed = max(time.time() - start, 1e-9)
                mb_s = (read_bytes / (1024 * 1024)) / elapsed
                logger.report_scalar("io_read", "mb_s", iteration=read_bytes, value=mb_s)
    elapsed = max(time.time() - start, 1e-9)
    return elapsed, read_bytes


def main():
    task = Task.init(project_name="AmSC", task_name="I/O bandwidth test")

    test_dir = _env_str("IO_TEST_DIR", "/tmp/")
    total_mb = _env_int("IO_TEST_SIZE_MB", 16384)
    chunk_mb = _env_int("IO_TEST_CHUNK_MB", 8)

    os.makedirs(test_dir, exist_ok=True)
    test_path = os.path.join(test_dir, "clearml_io_test.bin")

    total_bytes = total_mb * 1024 * 1024
    chunk_bytes = chunk_mb * 1024 * 1024

    write_time = _write_test(test_path, total_bytes, chunk_bytes)
    read_time, read_bytes = _read_test(test_path, chunk_bytes)

    write_mb_s = (total_mb / max(write_time, 1e-9))
    read_mb_s = ((read_bytes / (1024 * 1024)) / max(read_time, 1e-9))

    logger = Logger.current_logger()
    logger.report_scalar("io_summary", "write_mb_s", iteration=0, value=write_mb_s)
    logger.report_scalar("io_summary", "read_mb_s", iteration=0, value=read_mb_s)

    try:
        os.remove(test_path)
    except OSError:
        pass


if __name__ == "__main__":
    main()
