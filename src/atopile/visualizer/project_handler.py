import asyncio
import logging
from pathlib import Path
from typing import List

import watchfiles

from atopile.model.model import Model
from atopile.parser.parser import Builder
from atopile.project.project import Project
from atopile.visualizer.render import build_visualisation

log = logging.getLogger(__name__)

class ProjectHandler:
    def __init__(self):
        self.project: Project = None
        self.entrypoint_file = None
        self._entrypoint_block = None

        self._model: Model = None
        self._visualizer_dict = None

        self._task: asyncio.Task = None
        self._watchers: List[asyncio.Queue] = []

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
        if self._visualizer_dict is None:
            self.rebuild()
        return self._visualizer_dict

    @property
    def model(self) -> Model:
        if self._model is None:
            self.rebuild()
        return self._model

    def rebuild(self):
        log.info("Rebuilding model")
        self._model = Builder(self.project).build(self.entrypoint_file)
        self._visualizer_dict = build_visualisation(self._model, self.entrypoint_block)

    async def _watch_files(self):
        try:
            async for changes in watchfiles.awatch(self.project.root, self.project.get_std_lib_path()):
                log.info("Changes detected in project directory.")
                # figure out what source files have been updated
                changed_src_files = []
                for _, file in changes:
                    std_path = self.project.standardise_import_path(Path(file))
                    if std_path in self.model.src_files:
                        changed_src_files.append(std_path)

                if changed_src_files:
                    self.rebuild()
                    for queue in self._watchers:
                        await queue.put(self._visualizer_dict)
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
