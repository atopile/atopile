import asyncio
import logging
from pathlib import Path
from typing import List, AsyncIterator
import contextlib
import watchfiles
import ruamel.yaml

from atopile.model.model import Model
from atopile.parser.parser import build_model
from atopile.project.config import BuildConfig
from atopile.project.project import Project
from atopile.utils import timed, update_dict
from atopile.viewer.render import build_view

yaml = ruamel.yaml.YAML()
yaml.preserve_quotes = True

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ProjectHandler:
    def __init__(self):
        self.project: Project = None
        self.build_config: BuildConfig = None

        self._model: Model = None
        self._model_mutex = asyncio.Lock()

        self._watcher_task: asyncio.Task = None
        self._circuit_listener_queues: List[asyncio.Queue] = []
        self._ignore_files: List[Path] = []

    async def _build_model(self):
        with timed("Building model"):
            self._model = build_model(self.project, self.build_config)

    async def build_model(self):
        async with self._model_mutex:
            self._build_model()

    def get_model_sync(self) -> Model:
        """Return the model that's available or raise a RuntimeErorr if it's not"""
        if self._model is None:
            raise RuntimeError("No model available")
        return self._model

    async def get_model(self) -> Model:
        async with self._model_mutex:
            if self._model is None:
                await self._build_model()
            return self._model

    @staticmethod
    def _file_in_model_helper(filename: str, model: Model) -> bool:
        stringified_paths_in_model = [str(f) for f in model.src_files]
        return filename in stringified_paths_in_model

    async def file_in_model(self, filename: str) -> bool:
        return self._file_in_model_helper(filename, await self.get_model())

    def file_in_model_sync(self, filename: str) -> bool:
        return self._file_in_model_helper(filename, self.get_model_sync())

    def _get_config_helper(self, filename: str, model: Model) -> dict:
        # filename is expected to be ~/<project_root>/some_file.vis.json
        # to get the ato source file, let's strip the .json
        ato_filename = str(Path(filename).with_suffix("").with_suffix(".ato"))
        if not self._file_in_model_helper(ato_filename, model):
            raise FileNotFoundError

        vis_file = self.project.root / Path(filename).with_suffix(".yaml")

        if vis_file.exists():
            with vis_file.open() as f:
                vis_data = yaml.load(f)
        else:
            vis_data = {}

        return vis_data

    # TODO: cache configs and rate limit updates to FS
    async def get_config(self, filename: str):
        return self._get_config_helper(filename, await self.get_model())

    def get_config_sync(self, filename: str) -> dict:
        return self._get_config_helper(filename, self.get_model_sync())

    async def update_config(self, filename: str, updates: dict):
        # filename is expected to be ~/<project_root>/some_file.vis.json
        # to get the ato source file, let's strip the .json
        ato_filename = str(Path(filename).with_suffix("").with_suffix(".ato"))
        if not await self.file_in_model(ato_filename):
            raise FileNotFoundError

        vis_file = self.project.root / Path(filename).with_suffix(".yaml")

        if vis_file.exists():
            with vis_file.open() as f:
                vis_data = yaml.load(vis_file)
        else:
            vis_data = {}

        update_dict(vis_data, updates)

        self._ignore_files.append(vis_file)

        with vis_file.open("w") as f:
            yaml.dump(vis_data, f)

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

                if any(f in (await self.get_model()).src_files for f in updated_files):
                    await self.build_model()

                # empty the ignore list
                self._ignore_files.clear()

        except Exception as ex:
            log.exception(str(ex))
            raise

    @contextlib.contextmanager
    def monitor_filesystem(self):
        self._watcher_task = asyncio.create_task(self._watch_files())
        yield
        for queue in self._circuit_listener_queues:
            queue.put(asyncio.CancelledError)
        self._watcher_task.cancel()

    async def listen_for_circuits(self) -> AsyncIterator[dict]:
        queue = asyncio.Queue()
        self._circuit_listener_queues.append(queue)
        try:
            while True:
                visions = await queue.get()
                if isinstance(visions, asyncio.CancelledError) or visions == asyncio.CancelledError:
                    raise visions
                yield visions
        finally:
            self._circuit_listener_queues.remove(queue)

    async def build_circuit(self, path: str) -> dict:
        # TODO: throw error if path is not in model
        return build_view(
            await self.get_model(),
            self,
            path
        )
