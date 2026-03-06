from __future__ import annotations

from pathlib import Path

import pytest

from atopile.dataclasses import AppContext
from atopile.server.agent import package_workers


def _run(coro):
    import asyncio

    return asyncio.run(coro)


class _FakeTask:
    def done(self) -> bool:
        return False


def _fake_create_task(coro):
    coro.close()
    return _FakeTask()


@pytest.fixture(autouse=True)
def _clear_package_workers_state() -> None:
    package_workers._workers_by_id.clear()
    package_workers._parent_workers.clear()


class TestPackageWorkers:
    def test_spawn_package_worker_limits_concurrency(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        package_root = tmp_path / "packages" / "rp2350"
        package_root.mkdir(parents=True)
        (package_root / "ato.yaml").write_text("paths:\n  src: ./\n", encoding="utf-8")

        monkeypatch.setattr(package_workers.asyncio, "create_task", _fake_create_task)

        ctx = AppContext(workspace_paths=[tmp_path])
        setattr(ctx, "agent_session_id", "session-1")
        setattr(ctx, "agent_run_id", "run-1")

        for index in range(package_workers._config.subagent_max_concurrent):
            snapshot = _run(
                package_workers.spawn_package_worker(
                    ctx=ctx,
                    parent_session_id="session-1",
                    parent_run_id="run-1",
                    parent_project_root=tmp_path,
                    package_project_path="packages/rp2350",
                    goal=f"worker {index}",
                )
            )
            assert snapshot["status"] == "running"

        with pytest.raises(ValueError, match="At most"):
            _run(
                package_workers.spawn_package_worker(
                    ctx=ctx,
                    parent_session_id="session-1",
                    parent_run_id="run-1",
                    parent_project_root=tmp_path,
                    package_project_path="packages/rp2350",
                    goal="worker overflow",
                )
            )

    def test_spawn_package_worker_requires_real_package_project(
        self, tmp_path: Path
    ) -> None:
        ctx = AppContext(workspace_paths=[tmp_path])
        setattr(ctx, "agent_session_id", "session-1")
        setattr(ctx, "agent_run_id", "run-1")

        with pytest.raises(ValueError, match="Package project does not exist"):
            _run(
                package_workers.spawn_package_worker(
                    ctx=ctx,
                    parent_session_id="session-1",
                    parent_run_id="run-1",
                    parent_project_root=tmp_path,
                    package_project_path="packages/missing",
                    goal="Build wrapper",
                )
            )
