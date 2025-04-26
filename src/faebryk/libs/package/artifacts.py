import shutil
import tempfile
import zipfile
from pathlib import Path

import atopile.config


class Artifacts:
    path: Path

    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def build_artifacts(
        cfg: atopile.config.ProjectConfig, output_path: Path
    ) -> "Artifacts":
        """
        Build a zip file containing all the build artifacts.
        """

        # TODO: build targets should register their artifacts for inclusion here

        builds_dir = cfg.paths.build / "builds"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / "artifacts.zip"

            with zipfile.ZipFile(
                zip_path, mode="x", compression=zipfile.ZIP_BZIP2, compresslevel=9
            ) as zip_file:
                for file in builds_dir.glob("**/*"):
                    if file.is_file():
                        zip_file.write(file, file.relative_to(builds_dir))

            out_file = output_path / "artifacts.zip"
            if out_file.exists():
                out_file.unlink()
            out_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(zip_path, out_file)

            return Artifacts(out_file)

    @property
    def bytes(self) -> int:
        return self.path.stat().st_size
