# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from datetime import datetime, timedelta
from hashlib import md5
from pathlib import Path

from more_itertools import first

from atopile.cli.logging import ALERT
from atopile.config import config as Gcfg
from faebryk.libs.kicad.fileformats_latest import (
    C_kicad_footprint_file,
    C_kicad_fp_lib_table_file,
)
from faebryk.libs.picker.lcsc import (
    EasyEDA3DModel,
    EasyEDAAPIResponse,
    EasyEDAFootprint,
    EasyEDAPart,
    EasyEDASymbol,
)
from faebryk.libs.util import indented_container, once, robustly_rm_dir

logger = logging.getLogger(__name__)


class PartLifecycle:
    """

    ```
    EasyEDA API => easyeda2kicad => picker/lcsc.py
        -> build/cache/easyeda/parts/<id>/<id>.json => picker/lcsc.py
        -> build/cache/easyeda/parts/<id>/*.kicad*|.step => libs/app/pcb.py
        -> <component_lib>/footprints/atopile.pretty => transformer.py
        -> <layout_path>/<build>/<build>.kicad_pcb
    ```

    Notes:
     - `layout_path` determined by config.py (defaults to elec/layout)
     - `component_lib` determined by config.py (defaults to build/kicad/libs)
    """

    class EasyEDA_API:
        DELTA_REFRESH = timedelta(days=1)

        @property
        def _PATH(self) -> Path:
            return Gcfg.project.paths.build / "cache" / "parts" / "easyeda"

        def _get_part_path(self, partno: str) -> Path:
            return self._PATH.joinpath(partno) / f"{partno}.json"

        def _exists(self, partno: str) -> bool:
            return self._get_part_path(partno).exists()

        def shall_refresh(self, partno: str) -> bool:
            if not self._exists(partno):
                return True
            date_queried = self.load(partno).query_time
            return date_queried < datetime.now() - self.DELTA_REFRESH

        def ingest(self, partno: str, data: EasyEDAAPIResponse) -> EasyEDAAPIResponse:
            if self._exists(partno):
                existing = self.load(partno)
                # check whether footprint changed
                if existing.packageDetail.updateTime == data.packageDetail.updateTime:
                    return existing
                # TODO question user
                logger.warning(f"Updating cached {partno}")

            path = self._get_part_path(partno)
            data.dump(path)
            return data

        def load(self, partno: str) -> EasyEDAAPIResponse:
            return EasyEDAAPIResponse.load(self._get_part_path(partno))

    class Easyeda2Kicad:
        @property
        def _PATH(self) -> Path:
            return Gcfg.project.paths.build / "cache" / "parts" / "easyeda"

        def _get_part_path(self, partno: str) -> Path:
            return self._PATH.joinpath(partno)

        def get_fp_path(self, partno: str, footprint_name: str) -> Path:
            # public because needed by lcsc.py
            return self._get_part_path(partno) / f"{footprint_name}.kicad_mod"

        def _get_sym_path(self, partno: str, sym_name: str) -> Path:
            return self._get_part_path(partno) / f"{sym_name}.kicad_sym"

        def get_model_path(self, partno: str, model_name: str) -> Path:
            # public because needed by lcsc.py

            # TODO: Note: There are two names for models
            # 1. filename derived from footprint
            # 2. internal step file name
            # The only way to find out the internal is to download and read the step
            return self._get_part_path(partno) / f"{model_name}.step"

        def shall_refresh_model(self, part: EasyEDAPart) -> bool:
            # no model in api
            if not part.model and not part._pre_model:
                return False

            # TODO: consider timing out?
            if self.get_model_path(part.identifier, part.model_name).exists():
                return False

            return True

        def load_model(self, part: EasyEDAPart) -> EasyEDA3DModel:
            return EasyEDA3DModel.load(
                self.get_model_path(part.identifier, part.model_name)
            )

        def ingest_part(self, part: EasyEDAPart) -> EasyEDAPart:
            footprint = part.footprint
            fp_path = self.get_fp_path(part.identifier, part.footprint.base_name)
            if fp_path.exists():
                existing = EasyEDAFootprint.load(fp_path)
                if diff := existing.compare(footprint):
                    # TODO question user
                    logger.warning(
                        f"Updating cached footprint {part.footprint.base_name}:"
                        f" {indented_container(diff, recursive=True)}"
                    )
                    footprint.dump(fp_path)
            else:
                footprint.dump(fp_path)

            model_path = self.get_model_path(part.identifier, part.model_name)
            if part.model:
                part.model.dump(model_path)
            elif model_path.exists():
                part.model = EasyEDA3DModel.load(model_path)

            # TODO not sure about name
            sym_name = first(part.symbol.symbol.kicad_symbol_lib.symbols.keys())
            sym_path = self._get_sym_path(part.identifier, sym_name)
            # TODO actually check for changes
            if sym_path.exists():
                existing = EasyEDASymbol.load(sym_path)
                if diff := existing.compare(part.symbol):
                    # TODO question user
                    logger.warning(
                        f"Updating cached symbol {sym_name}:"
                        f" {indented_container(diff, recursive=True)}"
                    )
                    part.symbol.dump(sym_path)
            else:
                part.symbol.dump(sym_path)

            return part

    class Library:
        LIBNAME = "atopile"

        @property
        def _PATH(self) -> Path:
            # TODO change to parts later
            return Gcfg.project.paths.component_lib / "footprints" / "atopile.pretty"

        @property
        def fp_table(self) -> C_kicad_fp_lib_table_file:
            fp_table_path = Gcfg.build.paths.fp_lib_table
            if not fp_table_path.exists():
                fp_table = C_kicad_fp_lib_table_file.skeleton()
            else:
                fp_table = C_kicad_fp_lib_table_file.loads(fp_table_path)

            fppath = self._PATH
            fppath_rel = fppath.resolve().relative_to(
                Gcfg.build.paths.fp_lib_table.parent.resolve(),
                # FIXME set to false, only needed here because fps are in build
                # instead of in project dir
                walk_up=True,
            )

            uri = str(fppath_rel)
            assert not uri.startswith("/")
            assert not uri.startswith("${KIPRJMOD}")
            uri = "${KIPRJMOD}/" + uri

            if self.LIBNAME not in fp_table.fp_lib_table.libs:
                lib = C_kicad_fp_lib_table_file.C_fp_lib_table.C_lib(
                    name=self.LIBNAME,
                    type="KiCad",
                    uri=uri,
                    options="",
                    descr="atopile: atopile footprints",
                )
                fp_table.fp_lib_table.libs[self.LIBNAME] = lib
                # TODO move somewhere else
                logger.log(ALERT, "pcbnew restart required (updated fp-lib-table)")
            else:
                lib = fp_table.fp_lib_table.libs[self.LIBNAME]

            fp_table.dumps(fp_table_path)
            return fp_table

        def get_footprint(self, part: EasyEDAPart) -> tuple[Path, str]:
            # TODO use traits instead of eagerly modifying fp-lib-table
            lifecycle = PartLifecycle.singleton()

            eeda_path = lifecycle.easyeda2kicad.get_fp_path(
                part.identifier, part.footprint.base_name
            )
            fp = C_kicad_footprint_file.loads(eeda_path)
            mini_hash = md5(eeda_path.read_bytes()).hexdigest()[:6]
            _, name = fp.footprint.name.split(":", maxsplit=1)
            unique_name = f"{name}-{mini_hash}"
            fp.footprint.name = f"{self.LIBNAME}:{unique_name}"

            out_path = self._PATH / f"{unique_name}{eeda_path.suffix}"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            fp.dumps(out_path)

            return out_path, fp.footprint.name

        def __init__(self) -> None:
            # TODO remove
            self.fp_table

    class PCB:
        pass

    def __init__(self):
        self.easyeda_api = self.EasyEDA_API()
        self.easyeda2kicad = self.Easyeda2Kicad()
        self.library = self.Library()
        self.pcb = self.PCB()

        self._delete_deprecated_cache()

    def _delete_deprecated_cache(self):
        for path in (
            Gcfg.project.paths.build / "cache" / "easyeda",
            Gcfg.project.paths.component_lib / "footprints" / "lcsc.pretty",
            Gcfg.project.paths.component_lib / "lcsc.3dshapes",
        ):
            if path.exists():
                logger.warning(f"Deleting deprecated cache {path}")
                robustly_rm_dir(path)

        # FIXME ask user
        # fp_path = Gcfg.project.paths.component_lib / "footprints"
        # if fp_path.exists():
        #    logger.warning(f"Deleting deprecated library {fp_path}")
        # robustly_rm_dir(fp_path)

    @classmethod
    @once
    def singleton(cls) -> "PartLifecycle":
        return cls()
