from pathlib import Path

from faebryk.exporters.schematic import schematic as sch


def test_extract_declared_signals_from_source_locator_name_variants(
    tmp_path: Path,
) -> None:
    src = tmp_path / "part.ato"
    src.write_text(
        "\n".join(
            [
                "component Dummy:",
                "    signal X ~ pin 1",
                "",
                "component Texas_Instruments_TCA9548APWR_package:",
                "    signal A0 ~ pin 1",
                "    signal A1 ~ pin 2",
                "    signal A2 ~ pin 21",
                "    signal GND ~ pin 12",
                "    signal VCC ~ pin 24",
            ]
        ),
        encoding="utf-8",
    )

    expected = {"1": "A0", "2": "A1", "21": "A2", "12": "GND", "24": "VCC"}

    by_exact = sch._extract_declared_signals_from_source(
        src, "Texas_Instruments_TCA9548APWR_package"
    )
    assert by_exact == expected

    by_locator_tail = sch._extract_declared_signals_from_source(
        src, "i2c_mux.package|Texas_Instruments_TCA9548APWR_package"
    )
    assert by_locator_tail == expected


def test_extract_locator_source_and_component_prefers_leaf_segment(
    tmp_path: Path,
) -> None:
    app = tmp_path / "app.ato"
    part = tmp_path / "part.ato"
    app.write_text("component App:\n    pass\n", encoding="utf-8")
    part.write_text("component Leaf:\n    pass\n", encoding="utf-8")

    locator = f"{app}::App.mod|{app}::Wrapper.package|{part}::Leaf"
    source_path, component_name = sch._extract_locator_source_and_component(locator)

    assert source_path == part
    assert component_name == "Leaf"


def test_filter_pin_functions_by_signal_map_prefers_matching_signals() -> None:
    pin_number_to_functions = {
        "1": [
            {
                "name": "addressor.address_lines[0]",
                "type": "Signal",
                "is_line_level": True,
            },
            {"name": "power.hv", "type": "Power", "is_line_level": False},
        ],
        "12": [
            {
                "name": "addressor.address_lines[1]",
                "type": "Signal",
                "is_line_level": True,
            },
            {
                "name": "addressor.address_lines[2]",
                "type": "Signal",
                "is_line_level": True,
            },
            {"name": "power.lv", "type": "Power", "is_line_level": False},
        ],
        "21": [
            {
                "name": "addressor.address_lines[1]",
                "type": "Signal",
                "is_line_level": True,
            },
            {
                "name": "addressor.address_lines[2]",
                "type": "Signal",
                "is_line_level": True,
            },
        ],
    }
    signal_names = {
        "1": "A0",
        "12": "GND",
        "21": "A2",
    }

    filtered = sch._filter_pin_functions_by_signal_map(
        pin_number_to_functions,
        signal_names,
    )

    assert [fn["name"] for fn in filtered["1"]] == ["addressor.address_lines[0]"]
    assert [fn["name"] for fn in filtered["12"]] == ["power.lv"]
    assert [fn["name"] for fn in filtered["21"]] == ["addressor.address_lines[2]"]
