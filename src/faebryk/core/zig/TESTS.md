There are a bunch of tests `pytest .` failing.

# Strategy

- group tests by failure
- estimate difficulty to fix for each group
- describe in 2 sentences fix strategy and issue
- collect in this file (TESTS.md)
- stop (dont fix anything yet)

# Test Failure Groups

## Group 1: Missing PadDrill type (1 test) - EASY

**Issue**: PadDrill was simplified from a union to f64, but old code expects it as a struct
**Fix**: Re-export PadDrill as a simple type alias or restore as minimal struct

- test/libs/kicad/test_fileformats.py::test_empty_enum_positional
  **Comment**: This is what Pad.Drill was like in the old implementation (which worked):

```
        @dataclass
        class C_drill:
            class E_shape(SymEnum):
                circle = ""
                stadium = "oval"

            shape: E_shape = field(
                **sexp_field(positional=True), default=E_shape.circle
            )
            size_x: Optional[float] = field(**sexp_field(positional=True), default=None)
            size_y: Optional[float] = field(**sexp_field(positional=True), default=None)
            offset: Optional[C_xy] = None
```

    I suggest reproducing this format in zig

## Group 2: TypeError - **init**() takes 0 positional arguments (4 tests) - EASY

**Issue**: Structs only accept keyword arguments, but tests use positional args
**Fix**: Update test code to use kwargs

- test/exporters/pcb/kicad/test_pcb_transformer.py::TestTransformer::test_bbox
- test/exporters/schematic/kicad/test_schematic_transformer.py::test_wire_transformer
- test/exporters/netlist/kicad/test_netlist_kicad.py::test_netlist_t2
- test/exporters/netlist/kicad/test_netlist_kicad.py::test_netlist_graph

## Group 3: UnexpectedType errors in various parsers (45 tests) - MEDIUM

**Issue**: S-expression parser encountering unexpected field types or missing optional fields
**Fix**: Review and fix struct definitions to match actual KiCad file formats, particularly optional fields

- Error in 'kicad.pcb.Stackup': 3 tests
- Error in 'kicad.footprint.Footprint': 38 tests
- Error in 'kicad.symbol.SymbolLib': 3 tests
- Error in 'kicad.netlist.Component': 2 tests
- Error in 'kicad.schematic.Symbol': 1 test

## Group 4: Missing required field 'uuid' (2 tests) - EASY

**Issue**: Footprint struct expects uuid field but some files don't have it
**Fix**: Make uuid field optional in Footprint struct

- test/libs/kicad/test_fileformats.py::test_dump_load_equality[FootprintFile-path1]
- test/libs/kicad/test_fileformats.py::test_parser_pcb_and_footprints

## Group 5: Missing C_pcb_footprint attribute (5 tests) - MEDIUM

**Issue**: Code expects C_pcb_footprint constructor/class that doesn't exist
**Fix**: Check if this should be auto-generated or needs manual creation
SKIP FOR NOW

- test/exporters/bom/test_bom.py (5 tests)

## Group 6: ModuleNotFoundError faebryk.libs.sexp (1 test) - EASY

**Issue**: Old sexp module import path no longer exists
**Fix**: Update import to use new pyzig module path
SKIP FOR NOW, because we have no way to generate sexp for arbitrary objects that are not files

- test/libs/kicad/test_fileformats.py::test_embedded

## Group 7: Assertion errors in net naming tests (9 tests) - HARD

**Issue**: Net naming logic changed or not working as expected
**Fix**: Debug net naming algorithm and fix logic or update test expectations
SKIP FOR NOW

- test/end_to_end/test_net_naming.py (6 tests)
- test/end_to_end/test_net_name_determinism.py (1 test)
- test/end_to_end/test_pcb_export.py (4 tests)

## Group 8: subprocess.CalledProcessError in CLI tests (8 tests) - MEDIUM

**Issue**: atopile CLI commands failing during test execution
**Fix**: Fix underlying issues causing CLI failures (likely related to other groups)

- test/test_cli.py::test_app[default]
- test/test_examples.py (6 tests)

## Group 9: Clone errors in regression tests (2 tests) - EXTERNAL

**Issue**: Cannot clone external git repositories during tests
**Fix**: Check network/permissions or mock external dependencies
SKIP FOR NOW

- test/test_regressions.py (2 tests)

## Group 10: Literal folding assertion (1 test) - HARD

**Issue**: Solver/literal folding logic producing wrong results
**Fix**: Debug mathematical solver logic and fix calculation
SKIP FOR NOW

- test/core/solver/test_literal_folding.py::test_discover_literal_folding

## Group 11: Assert None is not None (1 test) - EASY

**Issue**: Test expecting non-None value but getting None
**Fix**: Check why parser returns None and fix return value

- test/libs/kicad/test_fileformats.py::test_parser_schematics

# Summary

- **Total failures**: 80 tests
- **Easy fixes**: 9 tests (Groups 1, 2, 4, 6, 11)
- **Medium fixes**: 54 tests (Groups 3, 5, 8)
- **Hard fixes**: 10 tests (Groups 7, 10)
- **External/blocked**: 2 tests (Group 9)
- **Unknown**: 5 performance tests (may be related to Group 3)

# Priority Order

1. Fix Group 2 (positional args) and Group 4 (uuid) first - easy wins
2. Fix Group 3 (UnexpectedType) - biggest impact
3. Fix Group 5 (C_pcb_footprint) - unblocks BOM tests
4. Fix Groups 6 and 1 - quick fixes
5. Debug Groups 7 and 10 - complex logic issues

============================================= short test summary info ==============================================
FAILED test/exporters/pcb/kicad/test_pcb_transformer.py::TestTransformer::test_bbox - TypeError
FAILED test/exporters/schematic/kicad/test_schematic_transformer.py::test_wire_transformer - TypeError: **init**() takes 0 positional arguments
FAILED test/exporters/schematic/kicad/test_schematic_transformer.py::test_get_symbol_file - ValueError: Error in 'kicad.symbol.SymbolLib': error.UnexpectedType
FAILED test/exporters/schematic/kicad/test_schematic_transformer.py::test_insert_symbol - ValueError: Error in 'kicad.symbol.SymbolLib': error.UnexpectedType
FAILED test/libs/kicad/test_fileformats.py::test_empty_enum_positional - AttributeError: module 'pyzig.pcb' has no attribute 'PadDrill'
FAILED test/libs/kicad/test_fileformats.py::test_dump_load_equality[PcbFile-path0] - ValueError: Error in 'kicad.pcb.Stackup': error.UnexpectedType
FAILED test/libs/kicad/test_fileformats.py::test_parser_netlist - ValueError: Error in 'kicad.netlist.Component': error.UnexpectedType
FAILED test/libs/kicad/test_fileformats.py::test_dump_load_equality[SchematicFile-path5] - ValueError: Error in 'kicad.schematic.Symbol': error.UnexpectedType
FAILED test/libs/kicad/test_fileformats.py::test_dump_load_equality[FootprintFile-path1] - ValueError: Missing required field 'uuid' in struct 'kicad.footprint.Footprint'
FAILED test/libs/kicad/test_fileformats.py::test_parser_schematics - assert None is not None
FAILED test/libs/kicad/test_fileformats.py::test_dump_load_equality[SymbolFile-path6] - ValueError: Error in 'kicad.symbol.SymbolLib': error.UnexpectedType
FAILED test/libs/kicad/test_fileformats.py::test_embedded - ModuleNotFoundError: No module named 'faebryk.libs.sexp'
FAILED test/libs/kicad/test_fileformats.py::test_dump_load_equality[NetlistFile-path2] - ValueError: Error in 'kicad.netlist.Component': error.UnexpectedType
FAILED test/libs/kicad/test_fileformats.py::test_parser_symbols - ValueError: Error in 'kicad.symbol.SymbolLib': error.UnexpectedType
FAILED test/libs/kicad/test_fileformats.py::test_parser_pcb_and_footprints - ValueError: Missing required field 'uuid' in struct 'kicad.footprint.Footprint'
FAILED test/libs/kicad/test_fileformats.py::test_write - ValueError: Error in 'kicad.pcb.Stackup': error.UnexpectedType
FAILED test/core/solver/test_solver.py::test_simple_pick - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/front_end/test_front_end_pick.py::test_ato_pick_resistor_shim - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/core/solver/test_literal_folding.py::test_discover_literal_folding - AssertionError: Mismatch ([0]) != ([1e-12, ∞])
FAILED test/front_end/test_front_end_pick.py::test_ato_pick_resistor - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/core/solver/test_solver.py::test_simple_negative_pick - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_module[Inductor[0]] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_module[MFR_TI_LMV321IDBVR] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_dependency_simple - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_module[LCSC_ID_C7972] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_module[Resistor[0]] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/front_end/test_front_end_pick.py::test_ato_pick_capacitor_shim - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_module[Inductor[1]] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/front_end/test_front_end_pick.py::test_ato_pick_capacitor - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/core/solver/test_solver.py::test_jlcpcb_pick_resistor - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_module[Resistor[1]] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/test_lcsc.py::TestLCSC::test_model_translations - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_skip_self_pick - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_module[Resistor[2]] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_type_pick - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/front_end/test_front_end_pick.py::test_ato_pick_inductor[SMDSize.I0402-L0402] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_dependency_advanced_1 - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/core/solver/test_solver.py::test_jlcpcb_pick_capacitor - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/end_to_end/test_net_naming.py::test_agreeing_net_names - AssertionError: assert 1 == 0
FAILED test/libs/picker/test_pickers.py::test_pick_module[Capacitor[0]] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/front_end/test_front_end_pick.py::test_ato_pick_inductor[SMDSize.SMD1_1x1_8mm-SMD1_1x1_8mm] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_capacitor_temperature_coefficient - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/libs/picker/test_pickers.py::test_pick_module[Capacitor[1]] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/end_to_end/test_net_name_determinism.py::test_net_names_deterministic - AssertionError: assert 1 == 0
FAILED test/front_end/test_front_end_pick.py::test_ato_pick_resistor_dependency - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/test_regressions.py::test_projects[https://github.com/atopile/spin-servo-drive] - test.test_regressions.CloneError
FAILED test/test_regressions.py::test_projects[https://github.com/atopile/packages] - test.test_regressions.CloneError
FAILED test/libs/picker/test_pickers.py::test_pick_dependency_advanced_2 - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/test_cli.py::test_app[default] - subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
FAILED test/front_end/test_front_end_pick.py::test_ato_pick_resistor_voltage_divider_fab - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/test_examples.py::test_examples_build[pick_parts] - subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
FAILED test/libs/picker/test_pickers.py::test_pick_dependency_div_negative - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/end_to_end/test_net_naming.py::test_duplicate_suggested_net_names - AssertionError: assert 1 == 0
FAILED test/libs/picker/test_pickers.py::test_null_solver - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/front_end/test_front_end_pick.py::test_ato_pick_resistor_voltage_divider_ato - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/end_to_end/test_net_naming.py::test_duplicate_specified_net_names - AssertionError: assert 'Net name collision' in 'Generated /home/needspeed/workspace/atopile/src/faebryk/core/zi...
FAILED test/test_examples.py::test_examples_build[i2c] - subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
FAILED test/test_examples.py::test_examples_build[layout_reuse] - subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
FAILED test/end_to_end/test_net_naming.py::test_conflicting_suggested_names_on_same_net - AssertionError: assert 1 == 0
FAILED test/end_to_end/test_net_naming.py::test_conflicting_net_names - AssertionError: assert 'Multiple conflicting required net names' in 'Generated /home/needspeed/workspace/atopil...
FAILED test/test_examples.py::test_examples_build[quickstart] - subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
FAILED test/test_examples.py::test_examples_build[equations] - subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
FAILED test/end_to_end/test_net_naming.py::test_differential_pair_suffixes - AssertionError: assert 1 == 0
FAILED test/end_to_end/test_pcb_export.py::test_empty_design - AssertionError: assert 1 == 0
FAILED test/end_to_end/test_pcb_export.py::test_pcb_file_created - AssertionError: assert 1 == 0
FAILED test/core/performance/test_performance_pick.py::test_performance_pick_real_module[_RP2040_Basic] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/end_to_end/test_pcb_export.py::test_pcb_file_addition - AssertionError: assert 1 == 0
FAILED test/test_examples.py::test_examples_build[esp32_minimal] - subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
FAILED test/end_to_end/test_pcb_export.py::test_pcb_file_removal - AssertionError: assert 1 == 0
FAILED test/exporters/bom/test_bom.py::test_bom_picker_pick - AttributeError: type object 'pyzig.pcb.KicadPcb' has no attribute 'C_pcb_footprint'
FAILED test/exporters/bom/test_bom.py::test_bom_explicit_pick - AttributeError: type object 'pyzig.pcb.KicadPcb' has no attribute 'C_pcb_footprint'
FAILED test/exporters/bom/test_bom.py::test_bom_kicad_footprint_no_lcsc - AttributeError: type object 'pyzig.pcb.KicadPcb' has no attribute 'C_pcb_footprint'
FAILED test/exporters/bom/test_bom.py::test_bom_kicad_footprint_lcsc_verbose - AttributeError: type object 'pyzig.pcb.KicadPcb' has no attribute 'C_pcb_footprint'
FAILED test/exporters/bom/test_bom.py::test_bom_kicad_footprint_lcsc_compact - AttributeError: type object 'pyzig.pcb.KicadPcb' has no attribute 'C_pcb_footprint'
FAILED test/exporters/netlist/kicad/test_netlist_kicad.py::test_netlist_t2 - TypeError: **init**() takes 0 positional arguments
FAILED test/exporters/netlist/kicad/test_netlist_kicad.py::test_netlist_graph - TypeError: **init**() takes 0 positional arguments
FAILED test/core/performance/test_performance_pick.py::test_performance_pick_real_module[RP2040_ReferenceDesign] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/core/performance/test_performance_pick.py::test_performance_pick_real_module[<lambda>] - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/core/performance/test_performance_pick.py::test_performance_pick_rc_formulas - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
FAILED test/core/solver/test_solver.py::test_solve_realworld_biggest - ValueError: Error in 'kicad.footprint.Footprint': error.UnexpectedType
================= 80 failed, 1333 passed, 27 skipped, 24 xfailed, 1 xpassed, 67 warnings in 32.31s =================
