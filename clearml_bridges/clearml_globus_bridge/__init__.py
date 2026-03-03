from typing import Any

__all__ = ["GlobusComputeLauncher"]


def __getattr__(name: str) -> Any:
    if name == "GlobusComputeLauncher":
        from .globus_compute_launcher import GlobusComputeLauncher

        return GlobusComputeLauncher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
