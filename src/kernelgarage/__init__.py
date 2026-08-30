"""kernelgarage: small tools for watching local LLMs and Pi hardware."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING

import typer

__all__ = ["__version__", "app", "main", "mcp_server"]

from kernelgarage.version import __version__

if TYPE_CHECKING:
    from kernelgarage import mcp_server

_SUBMODULES = frozenset({"mcp_server"})

app = typer.Typer(add_completion=False)


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


def __dir__() -> list[str]:
    return sorted(set(globals()) | _SUBMODULES)


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        print("Hello from kernelgarage!")


@app.command()
def report(
    hours: int = typer.Option(24, help="trailing window to report on"),
    html: bool = typer.Option(False, help="save as HTML instead of a terminal table"),
    out: Path = typer.Option(
        Path("report.html"), help="output path when --html is set"
    ),
) -> None:
    """Print a usage report, or save it as HTML."""
    from kernelgarage import mcp_server

    mcp_server.print_report(hours=hours, html=html, out=out)


def main() -> None:
    """Entry point for the `kernelgarage` console script."""
    app()
