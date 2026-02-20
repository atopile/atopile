// Fly.io Playground Spawner — zero npm deps
// Creates ephemeral web-IDE workspaces via Fly Machines API

const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const {
  PORT,
  FLY_API_TOKEN,
  WORKSPACE_APP,
  WORKSPACE_IMAGE,
  WORKSPACE_REGION,
  POOL_SIZE,
  MAX_IDLE_MS,
  MAX_LIFETIME_MS,
  CLEANUP_INTERVAL_MS,
  POOL_CHECK_INTERVAL_MS,
} = require("./lib/config");
const {
  parseCookies,
  verifyCookie,
  clearSessionCookie,
  setSessionCookie,
  json,
} = require("./lib/crypto");
const {
  listMachines,
  getMachine,
  destroyMachine,
  stopMachine,
} = require("./lib/machines");
const { createPoolManager } = require("./lib/pool");

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// In-memory session tracking: machineId → { created, lastSeen }
const sessions = new Map();

// Pre-warm pool: machine IDs that are started but not yet assigned to a user
const pool = new Set();

const state = { sessions, pool, poolReplenishing: false };
const { replenishPool, claimMachine } = createPoolManager(state);

// Load landing page HTML once at startup
const LANDING_HTML = fs.readFileSync(
  path.join(__dirname, "lib", "landing.html"),
  "utf8"
);

// ---------------------------------------------------------------------------
// Cleanup loop
// ---------------------------------------------------------------------------

async function cleanup() {
  try {
    const machines = await listMachines();
    const now = Date.now();
    const liveMachineIds = new Set();

    for (const m of machines) {
      if (m.config?.metadata?.playground !== "true") continue;
      liveMachineIds.add(m.id);
      // Don't clean up pool machines
      if (pool.has(m.id)) continue;

      const session = sessions.get(m.id);
      const created = session?.created || new Date(m.created_at).getTime();
      const lastSeen = session?.lastSeen || created;
      const idle = now - lastSeen;
      const alive = now - created;

      if (idle > MAX_IDLE_MS || alive > MAX_LIFETIME_MS) {
        console.log(
          `Cleaning up machine ${m.id} (idle=${Math.round(idle / 1000)}s, alive=${Math.round(alive / 1000)}s)`
        );
        sessions.delete(m.id);
        try {
          if (m.state === "started") await stopMachine(m.id);
          else await destroyMachine(m.id);
        } catch (err) {
          console.error(`Failed to clean up ${m.id}:`, err.message);
        }
      }
    }

    // Prune sessions for machines that no longer exist (destroyed externally)
    for (const [id] of sessions) {
      if (!liveMachineIds.has(id)) {
        console.log(`Pruning stale session for destroyed machine ${id}`);
        sessions.delete(id);
      }
    }
  } catch (err) {
    console.error("Cleanup error:", err.message);
  }
}

// ---------------------------------------------------------------------------
// HTTP server
// ---------------------------------------------------------------------------

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const cookies = parseCookies(req.headers.cookie);
  const machineId = verifyCookie(cookies.session);

  // Favicon
  if (url.pathname === "/favicon.svg" || url.pathname === "/favicon.ico") {
    res.writeHead(200, { "Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=86400" });
    res.end(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><g transform="matrix(0.20349758,0,0,0.19542038,2.446668,-3.609417)"><rect x="0" y="286.42" width="62.71" height="37.95" rx="2.5" transform="rotate(180,31.355,305.395)" fill="#f95015"/><path d="M184.16,64.43V45.06c0-5.13,4.16-9.29,9.29-9.29h85.86c5.13,0,9.29,4.16,9.29,9.29v96.45c0,5.13-4.16,9.29-9.29,9.29h-19.37c-5.13,0-9.29-4.16-9.29-9.29V83.21c0-5.13-4.16-9.29-9.29-9.29h-47.9c-5.13,0-9.29-4.16-9.29-9.29z" fill="#f95015"/><path d="M0,196.49v-19.37c0-5.13,4.16-9.29,9.29-9.29h44.13c5.13,0,9.29,4.16,9.29,9.29v40.72c0,5.13,4.16,9.29,9.29,9.29h32.59c5.13,0,9.29,4.16,9.29,9.29v40.72c0,5.13,4.16,9.29,9.29,9.29h118.19c5.13,0,9.29-4.16,9.29-9.29v-62.06c0-5.13-4.16-9.29-9.29-9.29h-50.2c-5.13,0-9.29-4.16-9.29-9.29v-47.44c0-5.13-4.16-9.29-9.29-9.29H140.5c-5.13,0-9.29-4.16-9.29-9.29V83.03c0-5.13-4.16-9.29-9.29-9.29H95.3c-5.13,0-9.29-4.16-9.29-9.29V45.08c0-5.13,4.16-9.29,9.29-9.29h62.55c5.13,0,9.29,4.16,9.29,9.29v47.44c0,5.13,4.16,9.29,9.29,9.29h32.42c5.13,0,9.29,4.16,9.29,9.29v47.44c0,5.13,4.16,9.29,9.29,9.29h51.88c5.13,0,9.29,4.16,9.29,9.29v137.97c0,5.13-4.16,9.29-9.29,9.29H86.26c-5.13,0-9.29-4.16-9.29-9.29v-40.72c0-5.13-4.16-9.29-9.29-9.29H35.09c-5.13,0-9.29-4.16-9.29-9.29v-40.72c0-5.13-4.16-9.29-9.29-9.29H9.29C4.16,205.78,0,201.62,0,196.49z" fill="#f95015"/><path d="M27.41,130.46v-19.37c0-5.13,4.16-9.29,9.29-9.29h67.58c5.13,0,9.29,4.16,9.29,9.29v47.44c0,5.13,4.16,9.29,9.29,9.29h35c5.13,0,9.29,4.16,9.29,9.29v40.72c0,5.13,4.16,9.29,9.29,9.29h43.37c5.13,0,9.29,4.16,9.29,9.29v19.37c0,5.13-4.16,9.29-9.29,9.29h-80.27c-5.13,0-9.29-4.16-9.29-9.29v-40.72c0-5.13-4.16-9.29-9.29-9.29H86.59c-5.13,0-9.29-4.16-9.29-9.29v-47.44c0-5.13-4.16-9.29-9.29-9.29h-31.3c-5.13,0-9.29-4.16-9.29-9.29z" fill="#f95015"/><rect x="27.41" y="35.77" width="37.95" height="37.95" rx="2.5" transform="rotate(180,46.38,54.75)" fill="#f95015"/></g></svg>`);
    return;
  }

  // Health check
  if (url.pathname === "/api/health") {
    return json(res, 200, {
      ok: true,
      sessions: sessions.size,
      pool: pool.size,
      uptime: Math.round(process.uptime()),
    });
  }

  // Spawn endpoint
  if (url.pathname === "/api/spawn" && req.method === "POST") {
    if (!FLY_API_TOKEN) {
      return json(res, 500, { error: "FLY_API_TOKEN not configured" });
    }
    try {
      const id = await claimMachine();
      sessions.set(id, { created: Date.now(), lastSeen: Date.now() });
      setSessionCookie(res, id);
      res.writeHead(302, { Location: "/" });
      res.end();
    } catch (err) {
      console.error("Spawn error:", err.message);
      json(res, 500, { error: "Failed to create workspace. Please try again." });
    }
    return;
  }

  // If user has a valid session cookie, replay to workspace
  if (machineId) {
    let session = sessions.get(machineId);

    // Re-validate machine exists if unknown or not checked recently (every 60s)
    const REVALIDATE_MS = 60 * 1000;
    const needsValidation =
      !session || Date.now() - (session.lastValidated || 0) > REVALIDATE_MS;

    if (needsValidation) {
      try {
        const machine = await getMachine(machineId);
        if (machine && machine.state === "started") {
          if (!session) {
            session = { created: Date.now(), lastSeen: Date.now(), lastValidated: Date.now() };
            sessions.set(machineId, session);
          } else {
            session.lastValidated = Date.now();
          }
        } else {
          // Machine is gone or stopped — clear cookie, show landing page
          sessions.delete(machineId);
          clearSessionCookie(res);
          res.writeHead(302, { Location: "/" });
          res.end();
          return;
        }
      } catch {
        sessions.delete(machineId);
        clearSessionCookie(res);
        res.writeHead(302, { Location: "/" });
        res.end();
        return;
      }
    }

    session.lastSeen = Date.now();
    res.writeHead(200, {
      "fly-replay": `app=${WORKSPACE_APP};instance=${machineId}`,
    });
    res.end();
    return;
  }

  // No session — serve landing page
  if (url.pathname === "/") {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(LANDING_HTML);
    return;
  }

  // Unknown route without session
  res.writeHead(302, { Location: "/" });
  res.end();
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

if (!FLY_API_TOKEN) {
  console.warn(
    "WARNING: FLY_API_TOKEN not set. Spawn endpoint will return errors."
  );
}

server.listen(PORT, () => {
  console.log(`Playground spawner listening on :${PORT}`);
  console.log(`  Workspace app:   ${WORKSPACE_APP}`);
  console.log(`  Workspace image: ${WORKSPACE_IMAGE}`);
  console.log(`  Region:          ${WORKSPACE_REGION}`);
  console.log(`  Pool size:       ${POOL_SIZE}`);
});

// Start pool replenishment and cleanup loops
replenishPool().catch((err) =>
  console.error("Initial pool replenishment failed:", err.message)
);
setInterval(() => replenishPool().catch(() => {}), POOL_CHECK_INTERVAL_MS);
setInterval(cleanup, CLEANUP_INTERVAL_MS);
