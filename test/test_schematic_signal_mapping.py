import os
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
                "    DVDD ~ pin 23",
            ]
        ),
        encoding="utf-8",
    )

    expected = {
        "1": "A0",
        "2": "A1",
        "21": "A2",
        "12": "GND",
        "23": "DVDD",
        "24": "VCC",
    }

    by_exact = sch._extract_declared_signals_from_source(
        src, "Texas_Instruments_TCA9548APWR_package"
    )
    assert by_exact == expected

    by_locator_tail = sch._extract_declared_signals_from_source(
        src, "i2c_mux.package|Texas_Instruments_TCA9548APWR_package"
    )
    assert by_locator_tail == expected

    by_locator_tail_with_trailing_dot = sch._extract_declared_signals_from_source(
        src, "i2c_mux.package|Texas_Instruments_TCA9548APWR_package."
    )
    assert by_locator_tail_with_trailing_dot == expected


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


def test_extract_locator_source_and_component_strips_trailing_punctuation(
    tmp_path: Path,
) -> None:
    app = tmp_path / "app.ato"
    part = tmp_path / "part.ato"
    app.write_text("component App:\n    pass\n", encoding="utf-8")
    part.write_text("component Leaf:\n    pass\n", encoding="utf-8")

    locator = f"{app}::App.mod|{part}::Leaf."
    source_path, component_name = sch._extract_locator_source_and_component(locator)

    assert source_path == part
    assert component_name == "Leaf"


def test_extract_locator_source_and_component_resolves_leaf_relative_to_parent_segment(
    tmp_path: Path,
) -> None:
    app = tmp_path / "pinout_test.ato"
    module_dir = tmp_path / "raspberry-rp2040"
    module_dir.mkdir(parents=True, exist_ok=True)
    module_file = module_dir / "raspberry-rp2040.ato"
    part_dir = module_dir / "parts" / "Raspberry_Pi_RP2040"
    part_dir.mkdir(parents=True, exist_ok=True)
    part_file = part_dir / "Raspberry_Pi_RP2040.ato"

    app.write_text("component App:\n    pass\n", encoding="utf-8")
    module_file.write_text("component Wrapper:\n    pass\n", encoding="utf-8")
    part_file.write_text(
        "component Raspberry_Pi_RP2040_package:\n    pass\n", encoding="utf-8"
    )

    locator = (
        f"{app.name}::PinoutTest.rp2040|"
        f"{module_file.relative_to(tmp_path)}::Raspberry_Pi_RP2040.package|"
        "parts/Raspberry_Pi_RP2040/Raspberry_Pi_RP2040.ato::Raspberry_Pi_RP2040_package"
    )
    cwd_before = Path.cwd()
    try:
        # Mirror real build behavior: resolver starts from project root cwd.
        os.chdir(tmp_path)
        source_path, component_name = sch._extract_locator_source_and_component(locator)
    finally:
        os.chdir(cwd_before)

    assert source_path == part_file
    assert component_name == "Raspberry_Pi_RP2040_package"


def test_extract_declared_signals_from_source_single_component_fallback(
    tmp_path: Path,
) -> None:
    src = tmp_path / "single_part.ato"
    src.write_text(
        "\n".join(
            [
                "component Raspberry_Pi_RP2040_package:",
                "    signal GPIO0 ~ pin 2",
                "    IOVDD ~ pin 1",
                "    signal GND ~ pin 57",
            ]
        ),
        encoding="utf-8",
    )

    extracted = sch._extract_declared_signals_from_source(src, "")
    assert extracted == {"1": "IOVDD", "2": "GPIO0", "57": "GND"}


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


def test_mark_passthrough_interfaces_for_shared_gpio_pin() -> None:
    iface_map = {
        "gpio[0]": {
            "type": "GPIO",
            "category": "control",
            "signals": set(),
            "pin_map": {
                "rp2040_package": {
                    "2": ("gpio[0]", "", True),
                }
            },
        },
        "uart": {
            "type": "UART",
            "category": "uart",
            "signals": {"tx"},
            "pin_map": {
                "rp2040_package": {
                    "2": ("uart", "tx", False),
                }
            },
        },
    }

    sch._mark_passthrough_interfaces(iface_map)

    assert iface_map["gpio[0]"].get("pass_through") is True
    assert "pass_through" not in iface_map["uart"]


def test_add_port_pins_to_internal_net_uses_back_pin_for_shared_gpio_bridge() -> None:
    module_interfaces = {
        "rp2040": {
            "gpio[0]": {
                "type": "GPIO",
                "category": "control",
                "signals": set(),
                "pin_map": {
                    "rp2040_package": {
                        "2": ("gpio[0]", "", True),
                    }
                },
            },
            "uart": {
                "type": "UART",
                "category": "uart",
                "signals": {"tx"},
                "pin_map": {
                    "rp2040_package": {
                        "2": ("uart", "tx", False),
                    }
                },
            },
        }
    }
    net = {
        "id": "uart_TX",
        "name": "uart-TX",
        "type": "signal",
        "pins": [
            {
                "componentId": "rp2040_package",
                "pinNumber": "2",
            }
        ],
    }

    enhanced, has_binding = sch._add_port_pins_to_internal_net(
        net=net,
        module_id="rp2040",
        module_interfaces=module_interfaces,
    )
    refs = {
        (p.get("componentId", ""), str(p.get("pinNumber", "")))
        for p in enhanced.get("pins", [])
    }

    assert has_binding is True
    assert ("rp2040_package", "2") in refs
    assert ("uart", "tx") in refs
    assert ("gpio[0]", "1") in refs
    assert ("gpio[0]", "2") in refs
