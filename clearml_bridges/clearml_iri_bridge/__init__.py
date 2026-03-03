from typing import Any

__all__ = ["IRILauncher"]


def __getattr__(name: str) -> Any:
    if name == "IRILauncher":
        from .iri_launcher import IRILauncher

        return IRILauncher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
