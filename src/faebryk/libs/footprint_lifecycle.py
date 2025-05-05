# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from datetime import datetime, timedelta
from pathlib import Path

from more_itertools import first

from atopile.config import config as Gcfg
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
        def get_footprint(self, part: EasyEDAPart) -> Path:
            lifecycle = PartLifecycle.singleton()
            return lifecycle.easyeda2kicad.get_fp_path(
                part.identifier, part.footprint.base_name
            )

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
