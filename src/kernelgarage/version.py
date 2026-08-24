__all__ = ["__version__"]

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as version_parser


def check_version(package_name: str) -> str | None:
    try:
        return version_parser(package_name)
    except PackageNotFoundError:
        # package is not installed
        return None


def detect_version() -> str:
    _version = check_version("kernelgarage")

    if _version is not None:
        return _version

    raise PackageNotFoundError("kernelgarage")


__version__ = detect_version()
