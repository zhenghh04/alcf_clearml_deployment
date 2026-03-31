from typing import Any

__all__ = ["IRILauncher", "build_job_payload", "build_alcf_job_payload"]


def __getattr__(name: str) -> Any:
    if name == "IRILauncher":
        from .iri_launcher import IRILauncher

        return IRILauncher
    if name == "build_job_payload":
        from .iri_launcher import build_job_payload

        return build_job_payload
    if name == "build_alcf_job_payload":
        from .iri_launcher import build_alcf_job_payload

        return build_alcf_job_payload
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
