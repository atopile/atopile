import asyncio
import logging
from pathlib import Path
from typing import List
import yaml
import time

import watchfiles

from atopile.model.model import Model
from atopile.parser.parser import Builder
from atopile.project.project import Project
from atopile.visualizer.render import build_visualisation

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

class ProjectHandler:
    def __init__(self):
        self.project: Project = None
        self.entrypoint_file = None
        self._entrypoint_block = None

        self._model: Model = None
        self._visualizer_dict = None
        self._vis_data: dict = None

        self._task: asyncio.Task = None
        self._watchers: List[asyncio.Queue] = []
        self._ignore_files: List[Path] = []
        self._request_requires_rebuild = False

    @property
    def entrypoint_block(self):
        if self._entrypoint_block is None:
            return str(self.project.standardise_import_path(self.entrypoint_file))
        return self._entrypoint_block

    @entrypoint_block.setter
    def entrypoint_block(self, value):
        self._entrypoint_block = value

    @property
    def visualizer_dict(self):
        if self._visualizer_dict is None or self._request_requires_rebuild:
            self.rebuild()
        return self._visualizer_dict

    @property
    def model(self) -> Model:
        if self._model is None or self._request_requires_rebuild:
            self.rebuild()
        return self._model

    def rebuild(self):
        start_time = time.time()
        log.info("Rebuilding everything...")
        # load vis data
        if self.vis_file_path.exists():
            with self.vis_file_path.open() as f:
                self._vis_data = yaml.safe_load(f)
        else:
            self._vis_data = {}

        # build the model
        self._model = Builder(self.project).build(self.entrypoint_file)

        # build the vision
        self._visualizer_dict = build_visualisation(self._model, self.entrypoint_block, self._vis_data)
        log.info(f"Rebuilt in {time.time() - start_time}s")
        self._request_requires_rebuild = False

    async def _watch_files(self):
        try:
            async for changes in watchfiles.awatch(self.project.root, self.project.get_std_lib_path()):
                log.info("Changes detected in project directory.")
                # figure out what source files have been updated
                changed_src_files = []
                for _, file in changes:
                    abs_path = Path(file).resolve().absolute()
                    if abs_path in self._ignore_files:
                        log.info(f"Ignoring file {abs_path}")
                        continue

                    std_path = self.project.standardise_import_path(abs_path)

                    if std_path in self.model.src_files:
                        changed_src_files.append(std_path)
                        break  # no need to check other files, we're rebuilding everything anyway

                    if abs_path == self.vis_file_path:
                        changed_src_files.append(self.vis_file_path)
                        break  # ditto

                if changed_src_files:
                    self.rebuild()
                    for queue in self._watchers:
                        await queue.put(self._visualizer_dict)

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

    def do_move(self, elementid, x, y):
        # as of writing, the elementid is the element's path
        # so just use that
        self._vis_data.setdefault(elementid, {})['position'] = {"x": x, "y": y}
        with self.vis_file_path.open('w') as f:
            yaml.dump(self._vis_data, f)
        self._ignore_files.append(self.vis_file_path)
        self._request_requires_rebuild = True
