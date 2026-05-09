from unified_eval import __version__


def test_package_imports() -> None:
    assert __version__ == "0.9.0-rc1"
