import pytest


@pytest.fixture(autouse=True)
def _prometheus_url_env(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_URL", "http://prometheus.test:9090")


@pytest.fixture(autouse=True)
def _evidence_log_env(monkeypatch, tmp_path):
    # Keeps every test's evidence log isolated to a temp file instead of the
    # real default under the developer's home directory.
    monkeypatch.setenv("KERNELGARAGE_EVIDENCE_LOG", str(tmp_path / "evidence.jsonl"))
