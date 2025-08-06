# KiCAD Plugin

## Overview

The KiCAD plugin provides layout synchronization functionality that allows reusing PCB layouts from sub-modules in atopile projects. This enables hierarchical PCB design where you can define a layout once and reuse it multiple times across your design.

## Layout Sync Workflow

### 1. Build Phase
During the atopile build process:
- The `generate_module_map()` function (in `src/atopile/layout.py`) scans the project for modules that have associated PCB layouts
- It creates a `.layouts.json` file that maps module addresses to their layout files
- A manifest file is generated containing references to the layouts.json file
- The build system can optionally auto-reload the PCB in KiCAD after building

### 2. Layout Map Structure
The layout map stored in `.layouts.json` contains entries for each module with a layout:
```json
{
  "module.address": {
    "layout_path": "/path/to/layout.kicad_pcb",
    "addr_map": {
      "source.component": "target.component"
    },
    "uuid_to_addr_map": {
      "uuid": "component.address"
    },
    "group_components": ["comp1", "comp2"],
    "nested_groups": ["nested.group1"]
  }
}
```

### 3. KiCAD Plugin Operation
The "Pull Group" plugin (`pullgroup.py`) performs the following:

1. **Group Synchronization** (`sync()` function):
   - Reads the layout map from the manifest
   - Creates PCB groups for each module in the layout map
   - Updates group membership to match the expected components

2. **Layout Pulling** (when user selects groups and runs "Pull Group"):
   - Loads the source layout file for each selected group
   - Generates net mappings between source and target boards
   - Syncs all PCB elements while preserving correct net connections

### 4. Element Synchronization
The plugin synchronizes various PCB elements:

- **Footprints** (`sync_footprints()`):
  - Matches footprints between source and target by address
  - Updates position, orientation, layer, and pad positions
  - Handles duplicate pad numbers by matching size and shape

- **Tracks** (`sync_track()`):
  - Copies track geometry (start, end, layer)
  - Updates net assignments using the generated net map

- **Zones** (`sync_zone()`):
  - Duplicates zone shapes and properties
  - Updates net assignments for copper zones

- **Drawings** (`sync_drawing()`):
  - Copies silkscreen and other graphical elements

### 5. Net Mapping
The `generate_net_map()` function creates mappings between source and target net names:
- Iterates through matching footprints in source and target
- Maps nets based on pad connections
- Handles conflicts by using the most frequently seen mapping
- Ensures electrical connectivity is preserved

### 6. Auto-reload Integration
After building, the system can automatically reload the PCB in KiCAD:
- Uses KiCAD's IPC interface (`src/faebryk/libs/kicad/ipc.py`)
- The `reload_pcb()` function triggers a refresh in open KiCAD instances
- Ensures the latest layout changes are immediately visible

## Development

It's much easier to work on this if you get proper static analysis setup.

To find `pcbnew`:
1. Open the scripting console in pcbnew
2. `import pcbnew`
3. `pcbnew.__file__`
4. Open up your workspace settings: Cmd + Shift + P -> "settings"
5. Remove the file name from the path in step 3
6. Add it like this:
```json
"python.analysis.extraPaths": [
    "<path-copied-from-step-5>"
]
```

KiCAD 8.0 still uses Python 3.9, so all code must be compatible with that.
