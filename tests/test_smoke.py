import app_name


def test_version() -> None:
    assert app_name.__version__ == "0.1.0"
