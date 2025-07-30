import subprocess
from pathlib import Path

import pcbnew  # type: ignore
import wx as wx_module  # type: ignore

from .common import LOG_FILE, log_exceptions, message_box, run_ato, setup_logger

log = setup_logger(__name__)

# print path to pcbnew
log.info(f"pcbnew: {pcbnew.__file__}")


class PullGroup(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Pull Group"
        self.category = "Pull Group Layout Atopile"
        self.description = (
            "Layout components on PCB in same spatial"
            " relationships as components on schematic."
            "Warning: this will save the PCB file."
        )
        self.show_toolbar_button = True
        self.icon_file_name = str(
            Path(__file__).parent.parent / "resource" / "download.png"
        )
        self.dark_icon_file_name = self.icon_file_name

    @log_exceptions()
    def Run(self):
        target_board: pcbnew.BOARD = pcbnew.GetBoard()
        board_path = target_board.GetFileName()

        cmd = [
            "kicad-ipc",
            "layout-sync",
            "--legacy",
            "--board",
            board_path,
        ]

        for selected in [g for g in target_board.Groups() if g.IsSelected()]:
            cmd.extend(["--include-group", selected.GetName()])
        for selected in [fp for fp in target_board.GetFootprints() if fp.IsSelected()]:
            uuid = selected.m_Uuid.AsString()
            cmd.extend(["--include-fp", uuid])

        # save pcb
        pcbnew.SaveBoard(board_path, target_board)

        try:
            # Run the command
            run_ato(cmd, cwd=Path(board_path).parent)
        except subprocess.CalledProcessError as e:
            log.error(f"Layout sync failed: {e}")
            log.error(f"stdout: {e.stdout}")
            log.error(f"stderr: {e.stderr}")

            # Show error message
            message_box(
                f"Layout sync failed, check '{LOG_FILE}' for details",
                "Pull Group Error",
                wx_module.OK | wx_module.ICON_ERROR,
            )
        except Exception:
            pass
        else:
            log.info("Layout sync successful")
