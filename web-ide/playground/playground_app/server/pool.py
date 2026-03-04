from __future__ import annotations

from dataclasses import dataclass

from playground_app.config import AppConfig
from playground_app.server.fly_machines import FlyMachine, FlyMachinesClient, MachinesApiError

CAPACITY_ERROR_MESSAGE = "No free machines available. Try later or install locally"


class CapacityError(RuntimeError):
    def __init__(self, code: str, message: str = CAPACITY_ERROR_MESSAGE):
        super().__init__(message)
        self.code = code


@dataclass
class Snapshot:
    active_count: int
    warm_count: int
    total_count: int


class PoolManager:
    def __init__(
        self,
        cfg: AppConfig,
        machines: FlyMachinesClient,
        pool_ids: set[str],
    ):
        self.cfg = cfg
        self.machines = machines
        self.pool_ids = pool_ids
        self.replenishing = False

    @staticmethod
    def compute_warm_target(strategy: str, target_n: int, active_count: int) -> int:
        if strategy == "absolute":
            return target_n
        if active_count == 0:
            return 1
        return (target_n * active_count) // (100 - target_n)

    @staticmethod
    def cap_warm_target(
        warm_target: int,
        active_count: int,
        max_machine_count: int | None,
    ) -> int:
        if max_machine_count is None:
            return max(0, warm_target)
        return max(0, min(warm_target, max_machine_count - active_count))

    @staticmethod
    def is_started_playground(machine: FlyMachine) -> bool:
        metadata = (machine.config or {}).get("metadata", {})
        return machine.state == "started" and metadata.get("playground") == "true"

    async def _snapshot(self, fail_closed: bool = False) -> Snapshot:
        try:
            machines = await self.machines.list_machines(fail_on_error=fail_closed)
        except MachinesApiError as exc:
            if fail_closed:
                raise CapacityError("CAPACITY_CHECK_FAILED") from exc
            raise

        started: list[FlyMachine] = []
        for machine in machines:
            if not self.is_started_playground(machine):
                continue
            if not FlyMachinesClient.extract_replay_state(machine):
                # Recycle legacy machines that predate replay-state enforcement.
                self.pool_ids.discard(machine.id)
                await self.machines.stop_machine(machine.id)
                continue
            started.append(machine)
        started_ids = {m.id for m in started}

        for pool_id in list(self.pool_ids):
            if pool_id not in started_ids:
                self.pool_ids.discard(pool_id)

        warm = 0
        active = 0
        for machine in started:
            if machine.id in self.pool_ids:
                warm += 1
            else:
                active += 1

        return Snapshot(active_count=active, warm_count=warm, total_count=active + warm)

    async def snapshot(self, fail_closed: bool = False) -> Snapshot:
        return await self._snapshot(fail_closed=fail_closed)

    def _desired_warm(self, active_count: int) -> int:
        warm_target = self.compute_warm_target(
            strategy=self.cfg.pool.strategy,
            target_n=self.cfg.pool.target_n,
            active_count=active_count,
        )
        return self.cap_warm_target(
            warm_target,
            active_count,
            self.cfg.pool.max_machine_count,
        )

    async def replenish_pool(self) -> None:
        if self.replenishing:
            return
        self.replenishing = True
        try:
            snapshot = await self._snapshot(fail_closed=True)
            desired_warm = self._desired_warm(snapshot.active_count)

            while len(self.pool_ids) < desired_warm:
                if (
                    self.cfg.pool.max_machine_count is not None
                    and snapshot.total_count >= self.cfg.pool.max_machine_count
                ):
                    break
                machine = await self.machines.create_machine()
                await self.machines.wait_for_machine(machine.id)
                self.pool_ids.add(machine.id)
                snapshot.total_count += 1
        finally:
            self.replenishing = False

    async def claim_machine(self) -> FlyMachine:
        for machine_id in list(self.pool_ids):
            self.pool_ids.discard(machine_id)
            machine = await self.machines.get_machine(machine_id)
            if machine and machine.state == "started" and FlyMachinesClient.extract_replay_state(machine):
                return machine
            if machine and machine.state == "started":
                await self.machines.stop_machine(machine.id)

        if self.cfg.pool.max_machine_count is not None:
            snapshot = await self._snapshot(fail_closed=True)
            if snapshot.total_count >= self.cfg.pool.max_machine_count:
                raise CapacityError("CAPACITY_EXHAUSTED")

        machine = await self.machines.create_machine()
        await self.machines.wait_for_machine(machine.id)
        return machine
