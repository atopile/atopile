# ZIG-Python integration

- [x] expose zig type in python bindings
- [x] shim PcbFile (zig) to C_kicad_pcb_file in fileformats.py
- [ ] Replace nested type references with zig types (e.g C_kicad_pcb_file.C_kicad_pcb -> KicadPcb)
- [ ] Find good way to shim HasPropertiesMixin
- [ ] Fix `propertys` field access - Zig uses arrays, Python expects dict-like access with `.get()` and `["key"]`
- [ ] Fix `skeleton()` method - TypeError: **init**() takes 0 positional arguments
- [ ] Add wrapper for property access patterns (e.g., `footprint.propertys["Reference"].value`)
- [ ] Handle None checks properly in shim properties
- [ ] Fix missing constructors/initializers for Zig types (General, Layer, Setup, etc.)
- [ ] Add support for creating Zig objects from Python (for skeleton and other creation methods)

# Test Failure Categories

## 1. Property Access Issues (Most Common)

- Tests expect `propertys` to be dict-like with `.get()` method
- Zig has `propertys` as an array of Property structs
- Affected tests:
  - test/end_to_end/test_pcb_export.py
  - test/exporters/pcb/kicad/test_pcb_transformer.py
  - test/libs/kicad/test_fileformats.py

## 2. Constructor/Initialization Issues

- `skeleton()` method tries to create Zig objects but constructors don't work
- TypeError: **init**() takes 0 positional arguments
- Need proper Python-callable constructors for Zig types

## 3. Build/Runtime Failures

- test/end_to_end tests fail during ato build process
- Possibly due to incomplete PCB file creation/manipulation

## 4. Missing Methods/Attributes

- Some properties/methods expected by Python code not present in Zig types
- Need to identify and add missing functionality

# Goal

okay i did the zig-python integration to replace C_kicad_pcb_file with our zig PcbFile.
There are a couple of tests failing due to some uncompleted tasks and bugs
Running `pytest` reveals 27 failing tests (was 33, 6 were fixed).
I suggest first looking for types of failures and adding more items to our integration checklist above.
Then fix the bugs that are not related to the above tasks (e.g segfault in test_parser_pcb_and_footprints).
