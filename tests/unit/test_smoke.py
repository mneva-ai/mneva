import mneva


def test_version_string() -> None:
    assert mneva.__version__ == "0.1.0"


def test_main_prints_banner(capsys) -> None:
    mneva.main()
    out = capsys.readouterr().out
    assert "Mneva v0.1.0" in out
    assert "https://mneva.org" in out
    assert "https://github.com/mneva-ai/mneva" in out


def test_tmp_home_fixture(tmp_mneva_home):
    assert tmp_mneva_home.exists()
    assert tmp_mneva_home.name == ".mneva"
