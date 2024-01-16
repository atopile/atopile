from atopile import config


def test_sanitise_dict_keys():
    """Test that dict keys are sanitised."""
    assert config._sanitise_dict_keys({"a-b": 1, "ato-version": {"e-f": 2}}) == {
        "a-b": 1,
        "ato_version": {"e-f": 2},
    }
