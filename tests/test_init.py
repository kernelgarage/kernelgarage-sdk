import pytest
from typer.testing import CliRunner

import kernelgarage

runner = CliRunner()


def test_main_prints_greeting():
    result = runner.invoke(kernelgarage.app, [])

    assert result.exit_code == 0
    assert result.output == "Hello from kernelgarage!\n"


def test_lazy_submodule_access():
    assert (
        kernelgarage.mcp_server.get_usage_report.__module__ == "kernelgarage.mcp_server"
    )


def test_dir_includes_lazy_submodule():
    assert "mcp_server" in dir(kernelgarage)


def test_unknown_attribute_raises():
    with pytest.raises(AttributeError):
        _ = kernelgarage.not_a_real_submodule


def test_report_subcommand_calls_print_report(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        kernelgarage.mcp_server,
        "print_report",
        lambda **kwargs: calls.append(kwargs),
    )
    out = tmp_path / "custom.html"

    result = runner.invoke(
        kernelgarage.app, ["report", "--hours", "6", "--html", "--out", str(out)]
    )

    assert result.exit_code == 0
    assert calls == [{"hours": 6, "html": True, "out": out}]


def test_main_invokes_app(monkeypatch):
    calls = []
    monkeypatch.setattr(kernelgarage, "app", lambda: calls.append(True))

    kernelgarage.main()

    assert calls == [True]
