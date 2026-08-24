import importlib
import importlib.metadata

import kernelgarage
from kernelgarage import version


def test_version_matches_installed_metadata():
    assert kernelgarage.__version__ == importlib.metadata.version("kernelgarage")


def test_falls_back_when_package_not_installed(monkeypatch):
    def raise_not_found(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", raise_not_found)
    importlib.reload(version)

    try:
        assert version.__version__ == "0.0.0"
    finally:
        monkeypatch.undo()
        importlib.reload(version)
