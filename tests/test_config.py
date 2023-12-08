from atopile import config


def test_sanitise_dict_keys():
    """Test that dict keys are sanitised."""
    assert config._sanitise_dict_keys({"a-b": 1, "c-d": {"e-f": 2}}) == {
        "a_b": 1,
        "c_d": {"e_f": 2},
    }
