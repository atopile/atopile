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
- [ ] test/libs/kicad/test_sexp.py
- [x] test/exporters/schematic/kicad/test_schematic_transformer.py (symbol)

# Defered

- [skip for now] src/faebryk/exporters/pcb/kicad/transformer.py
- [skip for now] src/faebryk/exporters/schematic/kicad/transformer.py
- [ ] src/faebryk/library/KicadFootprint.py (need to handle old version still)
- [ ] src/faebryk/library/PCB.py (need to handle old version still)
- [ ] src/faebryk/libs/ato_part.py (checksum)
- [ ] src/faebryk/libs/picker/lcsc.py (compare_without_uuid & v6 symbol)

look for kicad.sch

CAREFUL WITH DEEPCOPY

enums: handle sym vs str enums (maybe sexp field)
