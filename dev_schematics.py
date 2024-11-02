"""
Issues:

- [ ] Component references aren't aligned to anything in particular

- [ ] Add top-level global labels

- [x] Multiple net terminals of the same net

- [x] X/Y flips are dependent on the rotation of the part

- [x] Parts aren't being rotated properly

- [x] Battery's 180 degrees off

- [x] Unit should be 1, not 0

- [x] Placed off-sheet

- [x] Nets are netty

- [x] Global labels aren't being rotated appropriately
  They're actually only able to be aligned down or left.
  This seems like we should be adding net tags instead of global labels.

- [x] The net terminals appear to be on the wrong side of the parts
  (which is causing the wire cross-over)

- [x] Marking isn't reloading properly

- [x] Power pins aren't being properly detected

"""

import contextlib
import logging
import sys
from pathlib import Path

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.schematic.kicad.skidl.shims import Options
from faebryk.exporters.schematic.kicad.transformer import Transformer
from faebryk.libs.examples.buildutil import apply_design_to_pcb
from faebryk.libs.kicad.fileformats_sch import C_kicad_sch_file

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

root_dir = Path(__file__).parent
test_dir = root_dir / "test"
build_dir = root_dir / "build"

fp_lib_path_path = build_dir / "kicad/source/fp-lib-table"
sch_file = C_kicad_sch_file.skeleton()
# sch_file = C_kicad_sch_file.loads(test_dir / "common/resources/test.kicad_sch")


@contextlib.contextmanager
def add_to_sys_path(path):
    sys.path.append(str(path))
    yield
    sys.path.remove(str(path))


with add_to_sys_path(root_dir / "examples"):
    from minimal_led import App
app = App()
assert isinstance(app, Module)
assert isinstance(app.battery, F.Battery)
assert isinstance(app.led, F.PoweredLED)


app.led.led.add(F.has_descriptive_properties_defined({"LCSC": "C7429912"}))
app.led.current_limiting_resistor.add(
    F.has_descriptive_properties_defined({"LCSC": "C25077"})
)

apply_design_to_pcb(app)


full_transformer = Transformer(sch_file.kicad_sch, app.get_graph(), app)
full_transformer.index_symbol_files(fp_lib_path_path, load_globals=False)

options = Options(
    # draw_global_routing=True,
    draw_placement=True,
    draw_pin_names=True,
    # draw_routing=True,
    # draw_routing_channels=True,
    # draw_switchbox_boundary=True,
    # draw_switchbox_routing=True,
    retries=3,
    pin_normalize=True,
    net_normalize=True,
    compress_before_place=True,
    use_optimizer=True,
    use_push_pull=True,
    allow_jumps=True,
    align_parts=True,
    remove_overlaps=True,
    slip_and_slide=True,
    # rotate_parts=True,  # Doesn't work. It's forced on in a lower-level
    trim_anchor_pull_pins=True,
    # fanout_attenuation=True,
    # remove_power=True,
    # remove_high_fanout=True,
    normalize=True,
    flatness=1.0,
)

sch = full_transformer.generate_schematic(**options)

sch_file.dumps(build_dir / "kicad/source/test.kicad_sch")
