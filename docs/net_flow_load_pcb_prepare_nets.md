## Net attachment flow: KiCad ↔ graph

This document focuses only on the three net‑attachment phases in the build:

1. First KiCad→graph attach when the PCB is loaded.
2. Graph‑driven net creation/attachment from pad connectivity.
3. Second KiCad→graph attach plus name import and conflict‑free naming.

---

## 1. First KiCad attach (load KiCad PCB)

Entry point: `load_pcb` → `pcb.setup()`  
Files: `src/atopile/build_steps.py`, `src/faebryk/library/PCB.py`, `src/faebryk/exporters/pcb/kicad/transformer.py`

### What happens

- `F.PCB.setup`:
  - Loads the KiCad PCB (`kicad.loads`) and stores a pointer to the parsed `kicad.pcb.PcbFile` on the `F.PCB` instance.
  - Creates a `PCB_Transformer` with:
    - `pcb_file.kicad_pcb` (KiCad board model).
    - `app` (design root node).
  - Stores a pointer to the transformer.

- `PCB_Transformer.__init__`:
  - Configures internals (font, net number generator, etc.).
  - Immediately calls `self.attach()`.

- `PCB_Transformer.attach()`:
  - **Footprints & pads:**
    - Uses `map_footprints(tg, pcb)` to find KiCad footprints by `atopile_address`.
    - If the module already has `F.Footprints.has_associated_footprint`, attaches `F.KiCadFootprints.has_linked_kicad_footprint` to:
      - The logical footprint (`F.Footprints.GenericFootprint`).
      - The owning module.
    - Modules without `has_associated_footprint` only get the trait on the module (no logical footprint/pad binding yet).
    - For each `F.Footprints.GenericPad` child:
      - Resolves the corresponding KiCad pad(s) by pin name.
      - Attaches `F.KiCadFootprints.has_linked_kicad_pad` on the pad with pointers to:
        - The KiCad footprint and pad(s).
        - This `PCB_Transformer`.
  - **Nets (if any existing named nets):**
    - Calls `self.map_nets()` and then `self.bind_net(pcb_net, f_net)` for each mapping:
      - `map_nets()`:
        - Considers only `F.Net` instances that currently have `F.has_net_name`.
        - For each such net:
          - Uses `F.Net.get_connected_pads()` to find logical pads and footprints.
          - Follows `has_linked_kicad_pad` on each pad to get the corresponding KiCad pads.
          - For each KiCad pad, looks at `pcb_pad.net.name` and counts how many pads point to each KiCad net name.
        - Picks a “best” KiCad net name per fabll net if:
          - Exactly one candidate name dominates.
          - Its count is greater than `total_pads * match_threshold` (default 0.8; `match_threshold < 0.5` is rejected).
        - Builds `known_nets: dict[F.Net, KiCadNet]` for successful mappings.
      - `bind_net(kicad_net, f_net)`:
        - Attaches `F.KiCadFootprints.has_linked_kicad_net` to `f_net`, pointing to:
          - The KiCad net.
          - This transformer.

### Conflict & duplicate handling in this phase

- **Multiple fabll nets trying to map to the same KiCad net:**
  - `map_nets()` tracks a set `mapped_net_names` of KiCad net names that are already assigned.
  - For each fabll net:
    - It collects candidate KiCad net names from its pads.
    - Any candidate name already in `mapped_net_names` is removed from consideration.
    - If only names that already appear in `mapped_net_names` are found:
      - A warning is logged (`"Net name has already been used: ..."`) and no mapping is established for that fabll net.
  - Result: **at most one fabll net is mapped to each KiCad net name** during this phase.

- **No net created here:**
  - This phase does **not** create new `F.Net` instances.
  - It only maps pre‑existing, already‑named nets to KiCad nets where possible.

---

## 2. Graph‑driven net creation/attachment (from pad connectivity)

Entry point: `prepare_nets` → `attach_nets(app.tg)`  
File: `src/faebryk/exporters/netlist/graph.py`

### What happens

- `attach_nets(tg)`:
  - Collects all pad net interfaces:
    - Iterates `F.Footprints.GenericPad` instances.
    - For each pad, takes `pad.net.get()` (an `F.Electrical` interface).
  - Sorts those interfaces deterministically (`_get_stable_node_name`) so later bus grouping and naming are repeatable.
  - Calls `add_or_get_nets(*pad_mifs, tg=tg)` to return one canonical `F.Net` per bus of electrical connectivity (other nets on the same bus stay connected but are not part of the returned set).

- `add_or_get_nets(*interfaces, tg)`:
  - Groups interfaces into buses:
    - Uses `fabll.is_interface.group_into_buses(set(interfaces))`.
    - Each “bus” is a set of `F.Electrical` that are connected via interface connectivity (`_is_interface.connect_to`).
    - A representative interface (`bus_repr`) stands in for each bus.
  - For each bus, determines the net:
    - Checks for existing nets on that bus:
      - `nets_on_bus = F.Net.find_nets_for_mif(bus_repr.cast(F.Electrical))`
      - This returns any `F.Net` whose `part_of` interface is connected into that bus.
    - Cases:
      1. **No existing nets on the bus:**
         - Creates a new `F.Net` instance:
           - `F.Net.bind_typegraph(tg).create_instance(g=tg.get_graph_view())`.
         - Connects its `part_of` interface into the bus:
           - `net.part_of.get()._is_interface.get().connect_to(bus_repr)`.
         - `nets_on_bus` becomes `{net}`.
      2. **One existing net on the bus:**
         - Keeps that net; no new net is created.
      3. **Multiple existing nets on the same bus:**
         - Filters to “named” nets:
           - `named_nets_on_bus = {n for n in nets_on_bus if n.has_trait(F.has_overriden_name)}`
         - If no net has `F.has_overriden_name`:
           - Picks one deterministically:
             - `nets_on_bus = {min(nets_on_bus, key=_get_net_stable_key)}`.
           - The remaining nets on that bus are effectively ignored in future steps.
         - If exactly one net has `F.has_overriden_name`:
           - Uses that one; the other nets on the bus are ignored.
         - If **more than one named net** exists on the same bus:
           - Raises `KeyErrorAmbiguous("Multiple (named) nets interconnected")`.
  - Aggregates one chosen net per bus into `nets_out: set[F.Net]` and returns it (any other nets on that bus remain in the graph but are not used downstream).

### Conflict & duplicate handling in this phase

- **Multiple `F.Net` instances attached to the same electrical bus:**
  - If none of them are named (`F.has_overriden_name`):
    - The algorithm deterministically selects one (using `_get_net_stable_key`) and discards the others from consideration.
  - If exactly one is named:
    - That named net wins; all other nets on that bus are ignored.
  - If multiple nets are named:
    - The situation is treated as an error:
      - `KeyErrorAmbiguous` is raised with all named nets listed.
  - Result: **one canonical `F.Net` per bus is chosen for downstream use**, but any other nets on that bus still exist in the graph (they are just not returned/used later).

---

## 3. Second KiCad attach, net‑name import, and conflict‑free naming

Entry point: `prepare_nets` after `attach_nets`  
Files: `src/atopile/build_steps.py`, `src/faebryk/exporters/pcb/kicad/transformer.py`, `src/faebryk/libs/app/pcb.py`, `src/faebryk/exporters/netlist/graph.py`

### 3.1 Re‑running KiCad attach with the new nets

Code: `pcb.transformer.attach()` (same method as in step 1)

- Footprints and pads:
  - Re‑runs `map_footprints` and `bind_footprint`.
  - Ensures all modules/footprints/pads now reflect any changes introduced by earlier build steps (e.g. picking or net creation).

- Nets:
  - Re‑runs `map_nets()` + `bind_net()` just like in step 1, but now with:
    - Only nets that already have `F.has_net_name` at this moment.
    - Note: this call happens **before** `load_net_names` and `attach_net_names`, so freshly created nets without `has_net_name` are not mapped here.
  - Conflict handling is identical to step 1:
    - At most one fabll net is mapped to each KiCad net name.
    - Competing candidates for the same KiCad net name are dropped with a warning.

### 3.2 Importing KiCad net names (optional, `keep_net_names`)

Code: `load_net_names(app.g)`  
File: `src/faebryk/libs/app/pcb.py`

- What it does:
  - Iterates all `F.PCBTransformer.has_linked_kicad_net` traits.
  - For each:
    - Retrieves the fabll `F.Net`.
    - Reads the KiCad net’s `name`.
    - Attaches `F.has_net_name` to the fabll net with that string.
  - Collects all `(net → name)` pairs in `net_names: dict[F.Net, str]`.

- Duplicate‑name handling:
  - Detects duplicates in `net_names.values()` via `duplicates(...)`.
  - If duplicates exist:
    - Produces a message listing each duplicated name and its count.
    - Raises `UserResourceException("Multiple nets are named the same: ...")` if `raise_duplicates=True` (the default), upgrading duplicates to an error.
    - If `raise_duplicates=False`, the error is downgraded via `downgrade(...)`.
  - On success:
    - Every mapped `F.Net` now has a `F.has_net_name` trait set from the PCB.

### 3.3 Computing conflict‑free overridden net names

Code: `attach_net_names(nets)`  
File: `src/faebryk/exporters/netlist/graph.py`

This step generates final, human‑friendly, **unique** names for nets via `F.has_overriden_name`.

- Input set:
  - `nets` is the union of:
    - Nets created/collected by `attach_nets`.
    - Nets that gained names from `load_net_names` (when `keep_net_names` is enabled).

- Process (only the conflict‑relevant pieces):
  1. Deterministic ordering:
     - Sorts `nets` by `_get_net_stable_key` so all operations are reproducible.
  2. Classify nets:
     - Collects unnamed nets (no `F.has_overriden_name`) and their connected `F.Electrical` interfaces.
     - Registers nets that already have `F.has_overriden_name` as fixed‑name inputs.
  3. Base name selection:
     - For each unnamed net:
       - Extracts naming hints from connected interfaces:
         - `F.has_net_name` traits on interfaces/ancestors:
           - `Level.EXPECTED` → required names.
           - `Level.SUGGESTED` → suggestions with priority.
         - Implicit names from interface names and hierarchy.
       - If there are **multiple required names** for a single net:
         - Raises `UserException("Multiple conflicting required net names: ...")`.
       - If a single required name exists:
         - Uses it and immediately writes `F.has_overriden_name` to the net.
       - Otherwise:
         - Uses heuristics to pick a good base name from suggested/implicit candidates.
  4. Affixes:
     - Reads any `F.has_net_name_affix` traits on connected interfaces and applies:
       - `required_prefix`, `required_suffix` (e.g. diff pair `_P` / `_N`).
     - For very generic base names (`line`, `hv`, `unnamedX`, etc.) with affixes:
       - May replace the base name with a better interface‑derived name.
     - Power rails (`gnd`, `vcc`, etc.) are protected from affixes.
  5. Resolving name collisions between nets:
     - If multiple nets end up with the same candidate name:
       - `_resolve_conflicts_with_prefixes`:
         - Adds interface‑path‑based prefixes (owner module, anchor interface names, etc.).
       - `_resolve_conflicts_with_lca`:
         - Falls back to using a lowest common ancestor as a prefix.
       - `_resolve_conflicts_with_suffixes`:
         - Adds deterministic numeric suffixes where necessary.
  6. Apply final overridden names:
     - `_apply_names_to_nets`:
       - Truncates very long names for safety.
       - Creates `F.has_overriden_name` traits on each net with the final name.
     - Asserts that **every net in `nets` has `F.has_overriden_name`**.

### 3.4 Final duplicate check on primary net names

Code: `check_net_names(app.tg)`  
File: `src/faebryk/libs/app/pcb.py`

- What it checks:
  - Collects all `F.Net` instances that have `F.has_net_name`.
  - Groups them by `F.has_net_name.get_name()`.
  - If any name maps to more than one `F.Net`, it raises:
    - `UserResourceException("Net name collision: {net_name_collisions}")`.

- Relation to overridden names:
  - `F.has_net_name` is the primary / “external” net name (often from KiCad or explicit traits).
  - `F.has_overriden_name` is the internally generated, conflict‑free name from `attach_net_names`.
  - This final check ensures that **primary net names (`has_net_name`) are unique across the design**, even if overridden names also exist.

---

## Summary

- **Step 1 (first KiCad attach):**  
  - Maps existing named `F.Net` instances to KiCad nets via `has_linked_kicad_net`.  
  - Enforces “one fabll net per KiCad net name” and drops competing mappings with warnings.

- **Step 2 (graph‑driven net creation):**  
  - Builds `F.Net` from pad‑level `F.Electrical` connectivity.  
  - Chooses one canonical net per electrical bus for downstream steps (others on the same bus remain connected but are ignored); errors only if multiple named nets share a bus.

- **Step 3 (second KiCad attach + naming):**  
  - Re‑attaches footprints/pads and re‑maps only nets that already have `has_net_name`, again enforcing one fabll net per KiCad net name.  
  - Optionally imports KiCad net names (`has_net_name`), then computes conflict‑free overridden names (`has_overriden_name`).  
  - Finally, `check_net_names` rejects any remaining collisions at the `has_net_name` layer.
