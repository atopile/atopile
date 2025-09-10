- [x] src/faebryk/exporters/pcb/layout/heuristic_decoupling.py
- [ ] src/faebryk/exporters/pcb/layout/layout_sync.py
- [x] src/faebryk/importers/netlist/kicad/netlist_kicad.py
- [x] src/faebryk/libs/part_lifecycle.py
- [x] src/faebryk/libs/app/pcb.py
- [x] src/faebryk/libs/kicad/drc.py
- [x] src/faebryk/libs/kicad/ipc.py
- [x] test/end_to_end/test_pcb_export.py
- [x] test/exporters/netlist/kicad/test_netlist_kicad.py
- [x] test/exporters/pcb/kicad/test_pcb_transformer.py
- [ ] test/libs/kicad/test_fileformats.py
- [x] test/libs/kicad/test_sexp.py (not needed anymore)
- [x] test/exporters/schematic/kicad/test_schematic_transformer.py (symbol)
- [x] src/faebryk/library/KicadFootprint.py (need to handle old version still)
- [x] src/faebryk/library/PCB.py (need to handle old version still)
- [x] src/faebryk/libs/ato_part.py (checksum)

# Defered

- [skip for now] src/faebryk/exporters/pcb/kicad/transformer.py
- [skip for now] src/faebryk/exporters/schematic/kicad/transformer.py
- [ ] src/faebryk/libs/picker/lcsc.py (compare_without_uuid & v6 symbol)

justify/alignment: TEST
embedded/textbox
TextLayer(knockout)
layer/layers in geo

test checksum
| i think the lib fp checksum will make all boards components lose their position

load-dump roundtrip
| catchall
visit_dataclass
filter_fields

layout_reuse

# TESTS

FAILED test/core/solver/test_literal_folding.py::test_discover_literal_folding - AssertionError: Mismatch ([0]) != ([1e-12, ∞])
FAILED test/libs/kicad/test_fileformats.py::test_parser_schematics - assert None is not None
FAILED test/libs/kicad/test_fileformats.py::test_parser_pcb_and_footprints - AttributeError: module 'pyzig.footprint' has no attribute 'Attr'
FAILED test/libs/kicad/test_fileformats.py::test_embedded - ModuleNotFoundError: No module named 'faebryk.libs.sexp'
FAILED test/libs/kicad/test_fileformats.py::test_empty_enum_positional - ValueError: Invalid enum value
FAILED test/libs/kicad/test_fileformats.py::test_dump_load_equality[NetlistFile-path2] - assert '(export\n ...libraries)\n)' == '(export\n ...libraries)\n)'
FAILED test/end_to_end/test_pcb_export.py::test_pcb_file_removal - AssertionError: assert PcbSummary(nu...=['R1', 'R2']) == PcbSummary(nu...=['R1', 'R2'])
FAILED test/exporters/pcb/kicad/test_pcb_transformer.py::TestTransformer::test_bbox - TypeError
FAILED test/exporters/schematic/kicad/test_schematic_transformer.py::test_wire_transformer - assert 47 == (47 + 2)
FAILED test/exporters/schematic/kicad/test_schematic_transformer.py::test_get_symbol_file - AttributeError: 'pyzig.symbol.SymbolFile' object has no attribute 'kicad_symbol_lib'
FAILED test/exporters/schematic/kicad/test_schematic_transformer.py::test_insert_symbol - assert 22 == (22 + 1)
FAILED test/end_to_end/test_net_name_determinism.py::test_net_names_deterministic - AssertionError: [18:11:31] WARNING Your version of atopile (0.12.1) is out-of-date. Latest version: 0.12.4....
FAILED test/end_to_end/test_pcb_export.py::test_empty_design - AssertionError: assert PcbSummary(nu...footprints=[]) == PcbSummary(nu...footprints=[])
FAILED test/end_to_end/test_pcb_export.py::test_pcb_file_created - AssertionError: assert PcbSummary(nu...prints=['R1']) == PcbSummary(nu...prints=['R1'])
FAILED test/end_to_end/test_pcb_export.py::test_pcb_file_addition - AssertionError: assert PcbSummary(nu...prints=['R1']) == PcbSummary(nu...prints=['R1'])
FAILED test/test_examples.py::test_examples_build[esp32_minimal] - AssertionError: assert 2 in (0, 1)
