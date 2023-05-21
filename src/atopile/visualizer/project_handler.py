import asyncio
import logging
from pathlib import Path
from typing import List
import yaml
import time

import watchfiles

from atopile.model.model import Model
from atopile.parser.parser import build as build_model
from atopile.project.project import Project
from atopile.visualizer.render import build_visualisation

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ProjectHandler:
    def __init__(self):
        self.project: Project = None
        self.entrypoint_file = None
        self._entrypoint_block = None

        # TODO: these need mutexes
        self._model: Model = None
        self._current_vision = None
        self._vis_data: dict = None

        self._task: asyncio.Task = None
        self._watchers: List[asyncio.Queue] = []
        self._ignore_files: List[Path] = []

    @property
    def entrypoint_block(self):
        if self._entrypoint_block is None:
            return str(self.project.standardise_import_path(self.entrypoint_file))
        return self._entrypoint_block

    @entrypoint_block.setter
    def entrypoint_block(self, value):
        self._entrypoint_block = value

    @property
    def current_vision(self):
        if self._current_vision is None:
            self.rebuild_vision()
        return self._current_vision

    @property
    def vis_data(self) -> dict:
        if self._vis_data is None:
            self.reload_vis_data()
        return self._vis_data

    @property
    def model(self) -> Model:
        if self._model is None:
            self.rebuild_model()
        return self._model

    def reload_vis_data(self):
        start_time = time.time()
        log.info("Reloading vis_data...")
        # load vis data
        if self.vis_file_path.exists():
            with self.vis_file_path.open() as f:
                self._vis_data = yaml.safe_load(f)
        else:
            self._vis_data = {}
        log.info(f"Reloaded vis_data in {time.time() - start_time}s")

    def rebuild_model(self):
        start_time = time.time()
        log.info("Building model...")
        self._model = build_model(self.project, self.entrypoint_file)
        log.info(f"Rebuilt in {time.time() - start_time}s")

    def rebuild_vision(self):
        start_time = time.time()
        log.info("Building visualisation...")
        self._current_vision = build_visualisation(self.model, self.entrypoint_block, self.vis_data)
        log.info(f"Rebuilt in {time.time() - start_time}s")

    def rebuild_all(self):
        self.reload_vis_data()
        self.rebuild_model()
        self.rebuild_vision()

    async def _watch_files(self):
        try:
            async for changes in watchfiles.awatch(self.project.root, self.project.get_std_lib_path()):
                log.info("Changes detected in project directory.")
                # figure out what source files have been updated
                updated_files = []
                for _, file in changes:
                    abs_path = Path(file).resolve().absolute()
                    if abs_path in self._ignore_files:
                        log.info(f"Ignoring file {abs_path}")
                        continue

                    std_path = self.project.standardise_import_path(abs_path)
                    updated_files.append(std_path)

                if any(f in self.model.src_files for f in updated_files):
                    self.rebuild_model()

                if self.vis_file_path in updated_files:
                    self.reload_vis_data()

                if updated_files:
                    self.rebuild_vision()

                # empty the ignore list
                self._ignore_files.clear()

        except Exception as ex:
            log.exception(str(ex))
            raise

    def start_watching(self):
        self._task = asyncio.create_task(self._watch_files())

    def stop_watching(self):
        self._task.cancel()

    async def emit_visions(self) -> dict:
        queue = asyncio.Queue()
        self._watchers.append(queue)
        try:
            while True:
                visions = await queue.get()
                if isinstance(visions, asyncio.CancelledError) or visions == asyncio.CancelledError:
                    raise visions
                yield visions
        finally:
            self._watchers.remove(queue)

    def stop_vision_emission(self):
        for queue in self._watchers:
            queue.put(asyncio.CancelledError)

    # TODO: make this a cached property
    @property
    def vis_file_path(self) -> Path:
        return self.project.root / "vis.yaml"

    # TODO: move this to the class responsible for handling vis configs
    def do_move(self, elementid, x, y):
        # as of writing, the elementid is the element's path
        # so just use that
        self._vis_data.setdefault(elementid, {})['position'] = {"x": x, "y": y}
        with self.vis_file_path.open('w') as f:
            yaml.dump(self._vis_data, f)
        self._ignore_files.append(self.vis_file_path)
        asyncio.get_event_loop().call_soon(self.rebuild_vision)
