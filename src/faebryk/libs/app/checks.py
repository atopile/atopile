# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.exceptions import UserDesignCheckException, accumulate, downgrade

logger = logging.getLogger(__name__)


def check_design(
    tg: fbrk.TypeGraph,
    stage: F.implements_design_check.CheckStage,
    exclude: tuple[str, ...] = tuple(),
):
    """
    args:
        exclude: list of names of checks to exclude e.g:
        - `I2C.requires_unique_addresses`
    """
    logger.info(f"Running design checks for stage {stage.name}")

    with accumulate(UserDesignCheckException) as accumulator:
        for check in F.implements_design_check.bind_typegraph(tg).get_instances():
            with accumulator.collect():
                try:
                    check.run(stage)
                except F.implements_design_check.MaybeUnfulfilledCheckException as e:
                    with downgrade(UserDesignCheckException):
                        raise UserDesignCheckException.from_nodes(
                            str(e), e.nodes
                        ) from e
                except F.implements_design_check.UnfulfilledCheckException as e:
                    raise UserDesignCheckException.from_nodes(str(e), e.nodes) from e



class Test:

    class App(fabll.Node):
        _log_store: dict[int, list[str]] = {}
        is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

        def __preinit__(self):
            self.check_log = []

        def _ensure_log(self):
            key = self.instance.node().get_uuid()
            if key not in self._log_store:
                self._log_store[key] = []

        @property
        def check_log(self) -> list[str]:
            self._ensure_log()
            return self._log_store[self.instance.node().get_uuid()]

        @check_log.setter
        def check_log(self, value: list[str]):
            self._log_store[self.instance.node().get_uuid()] = value

        @F.implements_design_check.register_post_design_check
        def __check_post_design__(self):
            self._ensure_log()
            self.check_log.append("post_design")

        @F.implements_design_check.register_post_solve_check
        def __check_post_solve__(self):
            self._ensure_log()
            self.check_log.append("post_solve")
            raise UserDesignCheckException("Test exception")

        @F.implements_design_check.register_post_pcb_check
        def __check_post_pcb__(self):
            self._ensure_log()
            self.check_log.append("post_pcb")


    def test_design_checks(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        app = self.App.bind_typegraph(tg)
        a1 = app.create_instance(g=g)
        a2 = app.create_instance(g=g)

        check_design(tg, F.implements_design_check.CheckStage.POST_DESIGN)
        assert a1.check_log == ["post_design"]
        assert a2.check_log == ["post_design"]

        with pytest.raises(UserDesignCheckException):
            check_design(tg, F.implements_design_check.CheckStage.POST_SOLVE)
        assert a1.check_log == ["post_design", "post_solve"]
        assert a2.check_log == ["post_design", "post_solve"]

        check_design(tg, F.implements_design_check.CheckStage.POST_PCB)
        assert a1.check_log == ["post_design", "post_solve", "post_pcb"]
        assert a2.check_log == ["post_design", "post_solve", "post_pcb"]
