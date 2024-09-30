import contextlib
import sys
from pathlib import Path

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.schematic.kicad.transformer import Transformer
from faebryk.libs.kicad.fileformats_sch import C_kicad_sch_file

root_dir = Path(__file__).parent
test_dir = root_dir / "test"

fp_lib_path_path = test_dir / "common/resources/fp-lib-table"
sch_file = C_kicad_sch_file.loads(test_dir / "common/resources/test.kicad_sch")


@contextlib.contextmanager
def add_to_sys_path(path):
    sys.path.append(str(path))
    yield
    sys.path.remove(str(path))


# with add_to_sys_path(root_dir / "examples"):
#     from minimal_led import App
# app = App()
# assert isinstance(app, Module)

app = Module()

full_transformer = Transformer(sch_file.kicad_sch, app.get_graph(), app)
full_transformer.index_symbol_files(fp_lib_path_path, load_globals=False)

# mimicing typically design/user-space
audio_jack = full_transformer.app.add(Module())
pin_s = audio_jack.add(F.Electrical())
pin_t = audio_jack.add(F.Electrical())
pin_r = audio_jack.add(F.Electrical())
audio_jack.add(F.has_overriden_name_defined("U1"))

# mimicing typically lcsc code
sym = F.Symbol.with_component(
    audio_jack,
    {
        "S": pin_s,
        "T": pin_t,
        "R": pin_r,
    },
)
audio_jack.add(F.Symbol.has_symbol(sym))
sym.add(F.Symbol.has_kicad_symbol("test:AudioJack-CUI-SJ-3523-SMT"))

full_transformer.insert_symbol(audio_jack)

full_transformer.generate_schematic()
