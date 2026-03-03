from typing import Any

__all__ = ["GlobusComputeLauncher", "GlobusDataMover"]


def __getattr__(name: str) -> Any:
    if name == "GlobusComputeLauncher":
        from .globus_compute_launcher import GlobusComputeLauncher

        return GlobusComputeLauncher
    if name == "GlobusDataMover":
        from .globus_data_mover import GlobusDataMover

        return GlobusDataMover
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
