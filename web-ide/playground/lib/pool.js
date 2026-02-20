// Pre-warm machine pool — create/claim warm machines for fast session start.

const { FLY_API_TOKEN, POOL_SIZE } = require("./config");
const { createMachine, waitForMachine, getMachine } = require("./machines");

/**
 * Create a pool manager bound to shared state.
 * @param {{ sessions: Map, pool: Set, poolReplenishing: boolean }} state
 */
function createPoolManager(state) {
  async function replenishPool() {
    if (state.poolReplenishing || !FLY_API_TOKEN) return;
    state.poolReplenishing = true;
    try {
      // Clean up pool entries for machines that no longer exist
      for (const id of state.pool) {
        const m = await getMachine(id);
        if (!m || m.state !== "started") {
          console.log(`Pool: removing dead machine ${id}`);
          state.pool.delete(id);
        }
      }

      // Create machines until pool is full
      while (state.pool.size < POOL_SIZE) {
        console.log(`Pool: creating warm machine (pool=${state.pool.size}/${POOL_SIZE})...`);
        try {
          const machine = await createMachine();
          console.log(`Pool: machine ${machine.id} created, waiting for start...`);
          await waitForMachine(machine.id);
          console.log(`Pool: machine ${machine.id} ready`);
          state.pool.add(machine.id);
        } catch (err) {
          console.error("Pool: failed to create warm machine:", err.message);
          break; // avoid tight retry loop on persistent errors
        }
      }
    } finally {
      state.poolReplenishing = false;
    }
  }

  // Claim a machine from the pool, or create one on demand
  async function claimMachine() {
    // Try to grab a pre-warmed machine
    for (const id of state.pool) {
      state.pool.delete(id);
      const m = await getMachine(id);
      if (m && m.state === "started") {
        console.log(`Claimed pre-warmed machine ${id} from pool`);
        // Trigger pool replenishment in the background
        replenishPool().catch(() => {});
        return id;
      }
      console.log(`Pool machine ${id} is gone, skipping`);
    }

    // No pool machine available — create on demand
    console.log("Pool empty, creating machine on demand...");
    const machine = await createMachine();
    console.log(`Machine ${machine.id} created, waiting for start...`);
    await waitForMachine(machine.id);
    console.log(`Machine ${machine.id} started`);

    // Trigger pool replenishment in the background
    replenishPool().catch(() => {});
    return machine.id;
  }

  return { replenishPool, claimMachine };
}

module.exports = { createPoolManager };
