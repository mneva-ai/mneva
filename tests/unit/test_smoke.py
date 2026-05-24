import re

import mneva


def test_version_string() -> None:
    # Don't hardcode the number — it goes stale every release (that staleness is
    # exactly how the 0.1.3->0.2.0 version drift slipped through). Assert a
    # well-formed semver so a missing/empty/garbage version fails loudly instead.
    assert re.fullmatch(r"\d+\.\d+\.\d+", mneva.__version__)


def test_main_prints_banner(capsys) -> None:
    mneva.main()
    out = capsys.readouterr().out
    assert f"Mneva v{mneva.__version__}" in out
    assert "https://mneva.org" in out
    assert "https://github.com/mneva-ai/mneva" in out


def test_tmp_home_fixture(tmp_mneva_home):
    assert tmp_mneva_home.exists()
    assert tmp_mneva_home.name == ".mneva"
