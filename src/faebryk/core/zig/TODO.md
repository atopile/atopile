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

pretty_sexp should emulate kicad

SEGFAULT since i enabled embedded_files and stuff

refactor encode to let bottom type build list (with name) instead of struct
[or in other words, invariant that root type is a struct]

# TESTS

FAILED test/core/solver/test_literal_folding.py::test_discover_literal_folding - AssertionError: Mismatch ([0]) != ([1e-12, ∞])
FAILED test/core/solver/test_literal_folding.py::test_can_evaluate_literals - decimal.InvalidOperation: [<class 'decimal.InvalidOperation'>]

FAILED test/libs/kicad/test_fileformats.py::test_empty_enum_positional - ValueError: Invalid enum value
FAILED test/end_to_end/test_net_name_determinism.py::test_net_names_deterministic - AssertionError: assert -11 == 0
FAILED test/test_examples.py::test_examples_build[esp32_minimal] - AssertionError: assert 2 in (0, 1)
