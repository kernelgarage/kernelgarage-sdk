import pytest

import kernelgarage


def test_main_prints_greeting(capsys):
    kernelgarage.main()

    assert capsys.readouterr().out == "Hello from kernelgarage!\n"


def test_lazy_submodule_access():
    assert (
        kernelgarage.mcp_server.get_usage_report.__module__ == "kernelgarage.mcp_server"
    )


def test_unknown_attribute_raises():
    with pytest.raises(AttributeError):
        _ = kernelgarage.not_a_real_submodule
