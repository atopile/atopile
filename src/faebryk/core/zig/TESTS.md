There are a bunch of tests `pytest .` failing.

# Strategy

- go look at the one liner error in this file
- try to fix each of them (that appear easy)
- run `pytest .` to see which pass
- repeat 5 times

---

============================================= short test summary info ==============================================

- File "/home/needspeed/workspace/atopile/src/atopile/parser/AtoParser.py", line 17
  -AssertionError: assert 'Multiple conflicting required net names' in '[16:27:46] WARNING Your version of atopil...
  -AssertionError: assert 'Net name collision' in '[16:27:40] WARNING Your version of atopile (0.12.1) is out-of-...
  -AssertionError: assert 1 == 0
  -AssertionError: assert 1 == 0
  -AssertionError: assert 1 == 0
  -AssertionError: assert 1 == 0
  -AssertionError: assert 1 == 0
  -AssertionError: assert 1 == 0
  -AssertionError: assert 1 == 0
  -AssertionError: assert 1 == 0
  -AssertionError: assert 1 == 0
  -AssertionError: Mismatch ([0]) != ([1e-12, ∞])
  -AttributeError: module 'pyzig.footprint' has no attribute 'Attr'
  -ModuleNotFoundError: No module named 'faebryk.libs.sexp'
  -subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
  -subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
  -subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
  -subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
  -subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
  -subprocess.CalledProcessError: Command '['/home/needspeed/workspace/atopile/.venv/bin/python3', '-m', 'atopile'...
  -TypeError
  -ValueError: Missing required field 'width' in struct 'kicad.v6.symbol.Arc'
  -ValueError: Missing required field 'width' in struct 'kicad.v6.symbol.Arc'
  -ValueError: Missing required field 'width' in struct 'kicad.v6.symbol.Arc'
  -ValueError: Missing required field 'width' in struct 'kicad.v6.symbol.Arc'
  -ValueError: UnexpectedType in 'kicad.pcb.Stackup', field 'copper_finish': expected symbol or string for enum
  -ValueError: UnexpectedType in 'kicad.pcb.Stackup', field 'copper_finish': expected symbol or string for enum
  -ValueError: UnexpectedType in 'kicad.pcb.Stackup', field 'copper_finish': expected symbol or string for enum
  -ValueError: UnexpectedType in 'kicad.schematic.Symbol', field 'pin_names' at line 8: expected number for float
  -ValueError: UnexpectedType in 'kicad.schematic.Symbol', field 'pin_names' at line 8: expected number for float
  -ValueError: UnexpectedType in 'kicad.schematic.Symbol', field 'pin_names' at line 8: expected number for float
  -ValueError: UnexpectedType in 'kicad.schematic.Symbol', field 'pin_names' at line 8: expected number for float
  -ValueError: UnexpectedType in 'kicad.schematic.Symbol', field 'pin_names' at line 8: expected number for float
  -ValueError: UnexpectedType in 'kicad.schematic.Symbol', field 'pin_names' at line 8: expected number for float
  ERROR test/exporters/schematic/kicad/test_schematic_transformer.py::test_get_symbol_file
  ERROR test/exporters/schematic/kicad/test_schematic_transformer.py::test_index_symbol_files
  ERROR test/exporters/schematic/kicad/test_schematic_transformer.py::test_insert_symbol
  ERROR test/exporters/schematic/kicad/test_schematic_transformer.py::test_wire_transformer
  ERROR test/front_end
  FAILED test/core/solver/test_literal_folding.py::test_discover_literal_folding
  FAILED test/end_to_end/test_net_name_determinism.py::test_net_names_deterministic
  FAILED test/end_to_end/test_net_naming.py::test_agreeing_net_names
  FAILED test/end_to_end/test_net_naming.py::test_conflicting_net_names
  FAILED test/end_to_end/test_net_naming.py::test_conflicting_suggested_names_on_same_net
  FAILED test/end_to_end/test_net_naming.py::test_differential_pair_suffixes
  FAILED test/end_to_end/test_net_naming.py::test_duplicate_specified_net_names
  FAILED test/end_to_end/test_net_naming.py::test_duplicate_suggested_net_names
  FAILED test/end_to_end/test_pcb_export.py::test_empty_design
  FAILED test/end_to_end/test_pcb_export.py::test_pcb_file_addition
  FAILED test/end_to_end/test_pcb_export.py::test_pcb_file_created
  FAILED test/end_to_end/test_pcb_export.py::test_pcb_file_removal
  FAILED test/exporters/netlist/kicad/test_netlist_kicad.py::test_netlist_t2
  FAILED test/exporters/pcb/kicad/test_pcb_transformer.py::TestTransformer::test_bbox
  FAILED test/front_end/test_front_end_pick.py::test_ato_pick_inductor[SMDSize.I0402-L0402]
  FAILED test/front_end/test_front_end_pick.py::test_ato_pick_inductor[SMDSize.SMD1_1x1_8mm-SMD1_1x1_8mm]
  FAILED test/libs/kicad/test_fileformats.py::test_dump_load_equality[PcbFile-path0]
  FAILED test/libs/kicad/test_fileformats.py::test_dump_load_equality[SchematicFile-path5]
  FAILED test/libs/kicad/test_fileformats.py::test_dump_load_equality[SymbolFile-path6]
  FAILED test/libs/kicad/test_fileformats.py::test_embedded
  FAILED test/libs/kicad/test_fileformats.py::test_empty_enum_positional
  FAILED test/libs/kicad/test_fileformats.py::test_parser_pcb_and_footprints
  FAILED test/libs/kicad/test_fileformats.py::test_parser_schematics
  FAILED test/libs/kicad/test_fileformats.py::test_parser_symbols
  FAILED test/libs/kicad/test_fileformats.py::test_write
  FAILED test/libs/picker/test_pickers.py::test_pick_module[Inductor[0]]
  FAILED test/libs/picker/test_pickers.py::test_pick_module[Inductor[1]]
  FAILED test/test_examples.py::test_examples_build[equations]
  FAILED test/test_examples.py::test_examples_build[esp32_minimal]
  FAILED test/test_examples.py::test_examples_build[i2c]
  FAILED test/test_examples.py::test_examples_build[layout_reuse]
  FAILED test/test_examples.py::test_examples_build[pick_parts]
  FAILED test/test_examples.py::test_examples_build[quickstart]
