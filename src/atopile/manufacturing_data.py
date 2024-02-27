"""
This script largely controls the KiCAD CLI to generate
gerbers/drill files/etc... required to make circuit boards
"""

import logging
import re
import subprocess
import sys
import zipfile
from os import PathLike
from pathlib import Path
from time import time
from typing import Optional

import git

import atopile.errors
from atopile import config

log = logging.getLogger(__name__)


def find_kicad_cli() -> PathLike:
    """Figure out what to call for the KiCAD CLI."""
    if sys.platform.startswith("darwin"):
        kicad_cli_candidates = list(Path("/Applications/KiCad/").glob("**/kicad-cli"))
        # FIXME: handle multiple candidates
        return kicad_cli_candidates[0]
    elif sys.platform.startswith("linux"):
        return "kicad-cli"  # assume it's on the PATH


def run(*args, timeout_time: Optional[float] = 10, **kwargs) -> None:
    """Run a subprocess"""
    process = subprocess.Popen(
        *args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **kwargs
    )

    def _do_logging():
        outs, errs = process.communicate(timeout=0.1)
        for line in outs.splitlines():
            log.info(line)
        for line in errs.splitlines():
            log.error(line)

    start_time = time()
    while timeout_time is not None and time() - start_time < timeout_time:
        if process.poll() is not None:
            break
        try:
            _do_logging()
        except subprocess.TimeoutExpired:
            continue
    else:
        process.kill()

    exit_code = process.wait()
    _do_logging()

    if exit_code != 0:
        raise atopile.errors.AtoError(
            f"Command {args} failed with exit code {exit_code}"
        )


def generate_manufacturing_data(build_ctx: config.BuildContext) -> None:
    """Generate manufacturing data for the project."""
    # If there's no layout, we can't generate manufacturing data
    if not build_ctx.layout_path:
        atopile.errors.AtoError(
            "Layout must be available to generate manufacturing data"
        ).log(log, logging.WARNING)
        return

    # Ensure the build directory exists
    build_ctx.build_path.mkdir(parents=True, exist_ok=True)

    # Replace constants in the board file
    project_path = config.get_project_context().project_path
    try:
        repo = git.Repo(project_path, search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        atopile.errors.AtoError(
            "Project is not a git repository"
        ).log(log, logging.WARNING)
        short_githash = "nogit"
    else:
        short_githash_length = 7
        if repo.is_dirty():
            short_githash = "dirty"
        else:
            short_githash = repo.head.commit.hexsha[:short_githash_length]

    modded_kicad_pcb = build_ctx.output_base.with_suffix(
        ".kicad_pcb"
    )
    githash_kw = re.compile(re.escape("{{GITHASH}}"))
    with build_ctx.layout_path.open("r") as f_src, modded_kicad_pcb.open("w") as f_dst:
        for line in f_src:
            f_dst.write(githash_kw.sub(short_githash, line))

    # Setup for Gerbers
    gerber_dir = build_ctx.output_base.with_name(f"{build_ctx.output_base.name}-gerbers-{short_githash}")
    gerber_dir.mkdir(exist_ok=True, parents=True)
    gerber_dir_str = str(gerber_dir)
    if not gerber_dir_str.endswith("/"):
        gerber_dir_str += "/"

    kicad_cli = find_kicad_cli()

    # Generate Gerbers
    run([
        kicad_cli,
        "pcb",
        "export",
        "gerbers",
        "-o",
        gerber_dir_str,
        str(modded_kicad_pcb),
    ])
    run([
        kicad_cli,
        "pcb",
        "export",
        "drill",
        "-o",
        gerber_dir_str,
        str(modded_kicad_pcb),
    ])

    # Zip Gerbers
    zip_path = gerber_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for file in gerber_dir.glob("*"):
            zip_file.write(file)

    # Position files need some massaging for JLCPCB
    # We just need to replace the first row
    pos_path = build_ctx.output_base.with_suffix(".pos.csv")
    run([
        kicad_cli,
        "pcb",
        "export",
        "pos",
        "--format",
        "csv",
        "--units",
        "mm",
        "--use-drill-file-origin",
        "-o",
        str(pos_path),
        str(modded_kicad_pcb),
    ])
    pos_contents = pos_path.read_text().splitlines()
    pos_contents[0] = "Designator,Value,Package,Mid X,Mid Y,Rotation,Layer"
    pos_path.write_text("\n".join(pos_contents))
