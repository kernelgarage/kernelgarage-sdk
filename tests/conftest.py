import pytest


@pytest.fixture(autouse=True)
def _prometheus_url_env(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_URL", "http://prometheus.test:9090")
