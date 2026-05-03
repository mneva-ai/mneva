import mneva


def test_version_string() -> None:
    assert mneva.__version__ == "0.1.0a1"


def test_tmp_home_fixture(tmp_mneva_home):
    assert tmp_mneva_home.exists()
    assert tmp_mneva_home.name == ".mneva"
