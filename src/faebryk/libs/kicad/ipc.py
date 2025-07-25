import logging
import re
from pathlib import Path

from kipy import KiCad
from kipy.errors import ApiError, ConnectionError

from faebryk.libs.kicad.fileformat_config import C_kicad_config_common
from faebryk.libs.kicad.paths import get_config_common, get_ipc_socket_path
from faebryk.libs.sexp.util import prettify_sexp_string
from faebryk.libs.util import once, try_or

logger = logging.getLogger(__name__)

# https://gitlab.com/kicad/code/kicad-python
# https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/index.html


@once
def enable_plugin_api():
    cfg_file = get_config_common()
    cfg = C_kicad_config_common.from_json(cfg_file.read_text(encoding="utf-8"))
    if not cfg.api.enable_server:
        cfg.api.enable_server = True
        cfg_file.write_text(cfg.to_json(indent=2, ensure_ascii=False), encoding="utf-8")
        logger.warning(f"Enabled plugin api in {cfg_file}. Please restart KiCad.")


def _kicad_socket_files():
    return list(get_ipc_socket_path().glob("api*.sock"))


def _get_all_clients():
    socket_files = _kicad_socket_files()
    clients = [
        KiCad(socket_path=f"ipc://{socket_file}") for socket_file in socket_files
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
        def _cleanup(raw: str):
            out = raw
            # workaround for kicad memory not representing the same state as disk
            out = re.sub(r"\(version \d+\)", "", out)
            out = re.sub(r"\(generator .*\)", "", out)
            out = re.sub(r"\(generator_version .*\)", "", out)
            return prettify_sexp_string(out)

        reference = reference or self.path

        diskstate = _cleanup(
            reference.read_text(encoding="utf-8") if reference.exists() else ""
        )
        memorystate = _cleanup(self.board.get_as_string())

        return diskstate != memorystate

    def reload(self, force: bool = False, reference: Path | None = None):
        if not force and self.has_pending_changes(reference):
            logger.warning(f"PCB `{self.path}` has unsaved changes, skipping reload")

            return

        self.board.revert()
        self.board.save()

    @classmethod
    def from_client(cls, client: KiCad):
        try:
            client.get_board()
            return cls(client)
        except ApiError:
            return None

    def matches(self, pcb_path: Path):
        return self.path == pcb_path.expanduser().resolve().absolute()


def reload_pcb(pcb_path: Path, reference: Path | None = None):
    clients = _get_pcbnew_clients()
    matching = [pcbnew for pcbnew in clients if pcbnew.matches(pcb_path)]
    reloaded_pcb_news = []
    for pcbnew in matching:
        pcbnew.reload(reference=reference)
        reloaded_pcb_news.append(pcbnew)
    return reloaded_pcb_news
