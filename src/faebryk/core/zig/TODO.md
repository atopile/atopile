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

enums: handle sym vs str enums (maybe sexp field)

test checksum
load-dump roundtrip

- catchall

  handle old versions

- old user data (pcb)

visit_dataclass

deepcopy
