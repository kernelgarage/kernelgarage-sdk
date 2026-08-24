__all__ = ["__version__"]

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("kernelgarage")
except PackageNotFoundError:
    __version__ = "0.0.0"
