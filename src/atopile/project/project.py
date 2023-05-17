from pathlib import Path
from typing import Optional, Tuple

from atopile.utils import get_project_root

CONFIG_FILENAME = 'ato.yaml'
ATO_DIR_NAME = 'ato'
MODULE_DIR_NAME = 'ato.yaml'

def resolve_project_dir(path: Path):
    """
    Resolve the project directory from the specified path.
    """
    for p in [path] + list(path.parents):
        clean_path = p.resolve().absolute()
        if (clean_path / CONFIG_FILENAME).exists():
            return clean_path

class Project:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve().absolute()

    @property
    def project_config_path(self):
        return self.root / CONFIG_FILENAME

    @property
    def ato_dir(self):
        return self.root / ATO_DIR_NAME

    @property
    def module_dir(self):
        return self.ato_dir / MODULE_DIR_NAME

    @classmethod
    def from_path(cls, path: Path):
        """
        Create a Project from the specified path.
        """
        project_dir = resolve_project_dir(path)
        return cls(project_dir)

    def get_std_lib_path(self):
        # TODO: this will only work for editable installs
        return get_project_root() / "src/standard_library"

    def get_import_search_paths(self, cwp: Optional[Path] = None):
        if cwp is None:
            search_paths = [self.module_dir]
        else:
            if cwp.is_dir():
                search_paths = [cwp, self.module_dir]
            else:
                search_paths = [cwp.parent, self.module_dir]
        search_paths += [self.get_std_lib_path()]
        return search_paths

    def standardise_import_path(self, path: Path) -> Path:
        if path.is_relative_to(self.root):
            return path.resolve().absolute().relative_to(self.root)
        elif path.is_relative_to(self.get_std_lib_path()):
            return path.resolve().absolute().relative_to(self.get_std_lib_path())
        else:
            raise ImportError("Import is outside the project directory and isn't part of the std lib")

    def resolve_import(self, name: str, cwp: Optional[Path] = None) -> Tuple[Path, Path]:
        non_relative_paths = []
        for path in self.get_import_search_paths(cwp):
            abs_path = (path / name).resolve().absolute()
            if abs_path.exists():
                if not abs_path.is_relative_to(self.root):
                    non_relative_paths.append(abs_path)
                return abs_path, self.standardise_import_path(abs_path)

        if non_relative_paths:
            raise FileNotFoundError(f"Found {len(non_relative_paths)} files with name {name} in the import search paths, but none are within the project itself.")
        raise FileNotFoundError(name)
