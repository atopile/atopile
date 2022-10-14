# KiCAD symbol converter

This tool converts KiCAD6 symbol libraries to a faebryk component library.

## Usage
### Single
```bash
python3 main.py <path_to_kicad_library>.kicad_sym > <name_of_generated_lib>.py
```
### Bulk
```bash
bash convert_dir.sh <path_to_symbol_directory> <output_folder>
```
