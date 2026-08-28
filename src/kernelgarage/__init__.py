"""kernelgarage: small tools for watching local LLMs and Pi hardware."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

__all__ = ["__version__", "main", "mcp_server"]

from kernelgarage.version import __version__

if TYPE_CHECKING:
    from kernelgarage import mcp_server

_SUBMODULES = frozenset({"mcp_server"})


def __getattr__(name: str) -> object:
    """Lazily import feature submodules on first access (PEP 562).

    `import kernelgarage` alone stays cheap — `mcp_server` (and its `mcp`
    dependency) only loads once you actually touch it, e.g.
    `kernelgarage.mcp_server.mcp`.
    """
    if name in _SUBMODULES:
        module = importlib.import_module(f"kernelgarage.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def main() -> None:
    """Entry point for the `kernelgarage` console script."""
    print("Hello from kernelgarage!")
