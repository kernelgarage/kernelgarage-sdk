import kernelgarage


def test_main_prints_greeting(capsys):
    kernelgarage.main()

    assert capsys.readouterr().out == "Hello from kernelgarage!\n"
