import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from kipy import KiCad
from kipy.errors import ApiError, ConnectionError

from atopile.cli.logging_ import ALERT
from faebryk.libs.kicad.fileformat_config import C_kicad_config_common
from faebryk.libs.kicad.fileformats_latest import C_kicad_pcb_file
from faebryk.libs.kicad.paths import get_config_common, get_ipc_socket_path
from faebryk.libs.util import (
    compare_dataclasses,
    once,
    round_dataclass,
    sort_dataclass,
    try_or,
)

logger = logging.getLogger(__name__)

# https://gitlab.com/kicad/code/kicad-python
# https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/index.html


def running_in_kicad():
    return os.environ.get("KICAD_API_TOKEN") is not None


@once
def enable_plugin_api():
    cfg_file = get_config_common()
    cfg = C_kicad_config_common.from_json(cfg_file.read_text(encoding="utf-8"))
    if not cfg.api.enable_server:
        cfg.api.enable_server = True
        cfg_file.write_text(cfg.to_json(indent=2, ensure_ascii=False), encoding="utf-8")
        logger.warning(f"Enabled plugin api in {cfg_file}. Please restart KiCad.")


def _kicad_socket_files():
    base = get_ipc_socket_path()
    if sys.platform.startswith("win"):
        # named pipe
        pipes = [Path(p) for p in os.listdir(r"\\.\pipe\\")]
        out = [pipe for pipe in pipes if pipe.is_relative_to(base)]
    else:
        # unix socket
        out = list(base.glob("api*.sock"))
    return out


def _get_all_clients():
    socket_files = _kicad_socket_files()
    clients = [
        KiCad(socket_path=f"ipc://{socket_file}", timeout_ms=5000)
        for socket_file in socket_files
    ]
    # try connect
    clients = [
        client
        for client in clients
        if not try_or(client.ping, True, catch=ConnectionError)
    ]
    return clients


def _get_pcbnew_clients():
    clients = _get_all_clients()
    return [pcbnew for client in clients if (pcbnew := PCBnew.from_client(client))]


def _get_pcbnew_client_for_path(pcb_path: Path):
    clients = _get_pcbnew_clients()
    return [pcbnew for pcbnew in clients if pcbnew.matches(pcb_path)]


class PCBnew:
    def __init__(self, client: KiCad):
        self.client = client

    @property
    def board(self):
        return self.client.get_board()

    @property
    def path(self):
        return (
            (
                Path(self.board.document.project.path)
                / self.board.document.board_filename
            )
            .resolve()
            .absolute()
        )

    def has_pending_changes(self, reference: Path | None = None) -> bool:
        # This is hard
        return True

        def _cleanup(raw: str):
            out = C_kicad_pcb_file.loads(raw)
            for fp in out.kicad_pcb.footprints:
                fp.unknown = None

            out = round_dataclass(
                sort_dataclass(
                    out, sort_key=lambda x: getattr(x, "uuid", None) or str(x)
                ),
                6,
            )
            return out

        reference = reference or self.path

        diskstate = _cleanup(
            reference.read_text(encoding="utf-8") if reference.exists() else ""
        )
        memorystate = _cleanup(self.board.get_as_string())

        diff = compare_dataclasses(
            diskstate,
            memorystate,
            skip_keys=("uuid",),
        )
        return bool(diff)

    def reload(self, backup_path: Path | None = None):
        if backup_path:
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            client_id = (
                Path(self.client._client._socket_path)
                .name.removeprefix("api")
                .removeprefix("-")
                .removesuffix(".sock")
            ) or "0"
            path = backup_path.with_suffix(f".pcbnew-{client_id}.{now}.kicad_pcb")
            logger.log(
                ALERT,
                f"Backing up unsaved pcb changes to {path}",
            )
            self.board.save_as(str(path), overwrite=True, include_project=False)

        self.board.revert()

    @classmethod
    def from_client(cls, client: KiCad):
        try:
            client.get_board()
            return cls(client)
        except ApiError:
            return None

    def matches(self, pcb_path: Path):
        return self.path == pcb_path.expanduser().resolve().absolute()

    @classmethod
    def get_host(cls):
        if not running_in_kicad():
            raise Exception("Not running in KiCad")
        out = cls.from_client(KiCad())
        if not out:
            raise Exception("No PCBnew client found")
        return out


def opened_in_pcbnew(pcb_path: Path | None) -> bool:
    if not pcb_path:
        return bool(_get_pcbnew_clients())
    return bool(_get_pcbnew_client_for_path(pcb_path))


def reload_pcb(pcb_path: Path, backup_path: Path | None = None):
    clients = _get_pcbnew_client_for_path(pcb_path)
    for client in clients:
        client.reload(backup_path=backup_path)
