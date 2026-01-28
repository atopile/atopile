# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import time

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserDesignCheckException, accumulate, downgrade

logger = logging.getLogger(__name__)


def check_design(
    app: fabll.Node,
    stage: F.implements_design_check.CheckStage,
    exclude: tuple[str, ...] = tuple(),
):
    """
    Run design checks for a given stage.

    Args:
        app: The root application node
        stage: Which check stage to run (POST_INSTANTIATION_SETUP, POST_INSTANTIATION_DESIGN_CHECK, etc.)
        exclude: list of names of checks to exclude e.g:
            - `I2C.requires_unique_addresses`
    """
    checks = F.implements_design_check.bind_typegraph(app.tg).get_instances()

    with accumulate(UserDesignCheckException) as accumulator:
        for check in checks:
            with accumulator.collect():
                start_time = time.perf_counter()
                try:
                    check.run(stage)
                except F.implements_design_check.MaybeUnfulfilledCheckException as e:
                    with downgrade(UserDesignCheckException):
                        raise UserDesignCheckException.from_nodes(
                            str(e), e.nodes
                        ) from e
                except F.implements_design_check.UnfulfilledCheckException as e:
                    raise UserDesignCheckException.from_nodes(str(e), e.nodes) from e
                logger.debug(f"Ran {stage.name} check on {check.get_parent_force()[0].get_type_name()} in {(time.perf_counter() - start_time):.3f} seconds")


class Test:
    class _App(fabll.Node):
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

        @F.implements_design_check.register_post_instantiation_setup_check
        def __check_post_instantiation_setup__(self):
            self._ensure_log()
            self.check_log.append("post_instantiation_setup")

        @F.implements_design_check.register_post_instantiation_design_check
        def __check_post_instantiation_design_check__(self):
            self._ensure_log()
            self.check_log.append("post_instantiation_design_check")

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

        app = self._App.bind_typegraph(tg)
        a1 = app.create_instance(g=g)
        a2 = app.create_instance(g=g)

        # POST_INSTANTIATION_SETUP runs first (structure modifications)
        check_design(a1, F.implements_design_check.CheckStage.POST_INSTANTIATION_SETUP)
        assert a1.check_log == ["post_instantiation_setup"]
        assert a2.check_log == ["post_instantiation_setup"]

        # POST_INSTANTIATION_DESIGN_CHECK runs second (pure verification)
        check_design(a1, F.implements_design_check.CheckStage.POST_INSTANTIATION_DESIGN_CHECK)
        assert a1.check_log == ["post_instantiation_setup", "post_instantiation_design_check"]
        assert a2.check_log == ["post_instantiation_setup", "post_instantiation_design_check"]

        with pytest.raises(UserDesignCheckException):
            check_design(a1, F.implements_design_check.CheckStage.POST_SOLVE)
        assert a1.check_log == ["post_instantiation_setup", "post_instantiation_design_check", "post_solve"]
        assert a2.check_log == ["post_instantiation_setup", "post_instantiation_design_check", "post_solve"]

        check_design(a1, F.implements_design_check.CheckStage.POST_PCB)
        assert a1.check_log == [
            "post_instantiation_setup",
            "post_instantiation_design_check",
            "post_solve",
            "post_pcb",
        ]
        assert a2.check_log == [
            "post_instantiation_setup",
            "post_instantiation_design_check",
            "post_solve",
            "post_pcb",
        ]
