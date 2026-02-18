// Fly.io Playground Spawner — zero npm deps
// Creates ephemeral web-IDE workspaces via Fly Machines API

const http = require("node:http");
const https = require("node:https");
const crypto = require("node:crypto");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const PORT = parseInt(process.env.PORT || "8080", 10);
const FLY_API_TOKEN = process.env.FLY_API_TOKEN;
const WORKSPACE_APP = process.env.WORKSPACE_APP || "atopile-ws";
const WORKSPACE_IMAGE =
  process.env.WORKSPACE_IMAGE || "registry.fly.io/atopile-ws:latest";
const WORKSPACE_REGION = process.env.WORKSPACE_REGION || "iad";
const MAX_IDLE_MS = 30 * 60 * 1000; // 30 min
const MAX_LIFETIME_MS = 60 * 60 * 1000; // 60 min
const CLEANUP_INTERVAL_MS = 5 * 60 * 1000; // 5 min
const MACHINE_WAIT_TIMEOUT_S = 60;
const MACHINE_WAIT_RETRIES = 3; // 3 × 60s = 3 min max wait
const POOL_SIZE = parseInt(process.env.POOL_SIZE || "1", 10); // idle machines to keep warm
const POOL_CHECK_INTERVAL_MS = 30 * 1000; // check pool every 30s

// Derive HMAC secret from FLY_API_TOKEN so all spawner instances share it.
// If no token, fall back to random (local dev — sessions won't survive restart).
const HMAC_SECRET = FLY_API_TOKEN
  ? crypto.createHash("sha256").update(`playground-hmac:${FLY_API_TOKEN}`).digest()
  : crypto.randomBytes(32);
const MACHINES_API = "https://api.machines.dev";

// In-memory session tracking: machineId → { created, lastSeen }
const sessions = new Map();

// Pre-warm pool: machine IDs that are started but not yet assigned to a user
const pool = new Set();
let poolReplenishing = false;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function signCookie(machineId) {
  const tag = crypto
    .createHmac("sha256", HMAC_SECRET)
    .update(machineId)
    .digest("hex");
  return `${machineId}.${tag}`;
}

function verifyCookie(value) {
  if (!value) return null;
  const dot = value.lastIndexOf(".");
  if (dot === -1) return null;
  const machineId = value.substring(0, dot);
  const tag = value.substring(dot + 1);
  const expected = crypto
    .createHmac("sha256", HMAC_SECRET)
    .update(machineId)
    .digest("hex");
  if (!crypto.timingSafeEqual(Buffer.from(tag), Buffer.from(expected)))
    return null;
  return machineId;
}

function parseCookies(header) {
  const cookies = {};
  if (!header) return cookies;
  for (const part of header.split(";")) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    cookies[part.substring(0, eq).trim()] = part.substring(eq + 1).trim();
  }
  return cookies;
}

function clearSessionCookie(res) {
  res.setHeader(
    "Set-Cookie",
    "session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
  );
}

function setSessionCookie(res, machineId) {
  const signed = signCookie(machineId);
  res.setHeader(
    "Set-Cookie",
    `session=${signed}; HttpOnly; SameSite=Lax; Path=/; Max-Age=3600`
  );
}

function json(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

// ---------------------------------------------------------------------------
// Fly Machines API client
// ---------------------------------------------------------------------------

function machinesRequest(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, MACHINES_API);
    const payload = body ? JSON.stringify(body) : null;
    const req = https.request(
      url,
      {
        method,
        headers: {
          Authorization: `Bearer ${FLY_API_TOKEN}`,
          "Content-Type": "application/json",
          ...(payload ? { "Content-Length": Buffer.byteLength(payload) } : {}),
        },
      },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          const text = Buffer.concat(chunks).toString();
          try {
            resolve({ status: res.statusCode, data: JSON.parse(text) });
          } catch {
            resolve({ status: res.statusCode, data: text });
          }
        });
      }
    );
    req.on("error", reject);
    if (payload) req.write(payload);
    req.end();
  });
}

// Caddyfile with an additional plain-HTTP listener on :3080 for Fly proxy.
// Fly terminates TLS at the edge and forwards plain HTTP to internal_port.
const CADDYFILE = `{
\tdefault_sni {$WEB_IDE_PUBLIC_HOST:code-vm}
}

(atopile_proxy) {
\tlog {
\t\toutput stderr
\t}
\t@backend path /ws/* /api/* /health
\thandle @backend {
\t\treverse_proxy 127.0.0.1:8501
\t}
\thandle {
\t\treverse_proxy 127.0.0.1:3001
\t}
}

# Plain HTTP for Fly proxy (internal_port)
http://:3080 {
\timport atopile_proxy
}

# HTTPS for direct/local access
https://localhost:3443, https://127.0.0.1:3443, https://code-vm:3443, https://{$WEB_IDE_PUBLIC_HOST:code-vm}:3443 {
\ttls internal
\timport atopile_proxy
}
`;

function machineConfig() {
  return {
    image: WORKSPACE_IMAGE,
    auto_destroy: true,
    guest: { cpu_kind: "performance", cpus: 1, memory_mb: 2048 },
    files: [
      {
        guest_path: "/home/openvscode-server/.local/etc/Caddyfile",
        raw_value: Buffer.from(CADDYFILE).toString("base64"),
      },
    ],
    services: [
      {
        protocol: "tcp",
        internal_port: 3080,
        ports: [
          { port: 443, handlers: ["tls", "http"] },
          { port: 80, handlers: ["http"], force_https: true },
        ],
        concurrency: {
          type: "connections",
          soft_limit: 25,
          hard_limit: 30,
        },
        autostart: true,
        autostop: "stop",
      },
    ],
    restart: { policy: "on-failure", max_retries: 3 },
    metadata: { playground: "true" },
  };
}

async function createMachine() {
  const resp = await machinesRequest(
    "POST",
    `/v1/apps/${WORKSPACE_APP}/machines`,
    { region: WORKSPACE_REGION, config: machineConfig() }
  );
  if (resp.status !== 200) {
    throw new Error(
      `Machines API create failed (${resp.status}): ${JSON.stringify(resp.data)}`
    );
  }
  return resp.data;
}

async function waitForMachine(machineId) {
  for (let attempt = 0; attempt < MACHINE_WAIT_RETRIES; attempt++) {
    const resp = await machinesRequest(
      "GET",
      `/v1/apps/${WORKSPACE_APP}/machines/${machineId}/wait?state=started&timeout=${MACHINE_WAIT_TIMEOUT_S}`
    );
    if (resp.status === 200) return;
    // 408 = deadline exceeded, retry
    if (resp.status === 408) {
      console.log(
        `Machine ${machineId} not ready yet (attempt ${attempt + 1}/${MACHINE_WAIT_RETRIES}), retrying...`
      );
      continue;
    }
    throw new Error(
      `Machine wait failed (${resp.status}): ${JSON.stringify(resp.data)}`
    );
  }
  throw new Error("Machine failed to start within timeout");
}

async function listMachines() {
  const resp = await machinesRequest(
    "GET",
    `/v1/apps/${WORKSPACE_APP}/machines`
  );
  if (resp.status !== 200) return [];
  return Array.isArray(resp.data) ? resp.data : [];
}

async function getMachine(machineId) {
  const resp = await machinesRequest(
    "GET",
    `/v1/apps/${WORKSPACE_APP}/machines/${machineId}`
  );
  if (resp.status !== 200) return null;
  return resp.data;
}

async function destroyMachine(machineId) {
  await machinesRequest(
    "DELETE",
    `/v1/apps/${WORKSPACE_APP}/machines/${machineId}?force=true`
  );
}

async function stopMachine(machineId) {
  await machinesRequest(
    "POST",
    `/v1/apps/${WORKSPACE_APP}/machines/${machineId}/stop`
  );
}

// ---------------------------------------------------------------------------
// Pre-warm pool
// ---------------------------------------------------------------------------

async function replenishPool() {
  if (poolReplenishing || !FLY_API_TOKEN) return;
  poolReplenishing = true;
  try {
    // Clean up pool entries for machines that no longer exist
    for (const id of pool) {
      const m = await getMachine(id);
      if (!m || m.state !== "started") {
        console.log(`Pool: removing dead machine ${id}`);
        pool.delete(id);
      }
    }

    // Create machines until pool is full
    while (pool.size < POOL_SIZE) {
      console.log(`Pool: creating warm machine (pool=${pool.size}/${POOL_SIZE})...`);
      try {
        const machine = await createMachine();
        console.log(`Pool: machine ${machine.id} created, waiting for start...`);
        await waitForMachine(machine.id);
        console.log(`Pool: machine ${machine.id} ready`);
        pool.add(machine.id);
      } catch (err) {
        console.error("Pool: failed to create warm machine:", err.message);
        break; // avoid tight retry loop on persistent errors
      }
    }
  } finally {
    poolReplenishing = false;
  }
}

// Claim a machine from the pool, or create one on demand
async function claimMachine() {
  // Try to grab a pre-warmed machine
  for (const id of pool) {
    pool.delete(id);
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
// Landing page HTML
// ---------------------------------------------------------------------------

const LANDING_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>atopile playground</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0d1117;
    color: #c9d1d9;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .container {
    text-align: center;
    max-width: 480px;
    padding: 2rem;
  }
  h1 {
    font-size: 2.5rem;
    color: #58a6ff;
    margin-bottom: 0.5rem;
  }
  .tagline {
    color: #8b949e;
    font-size: 1.1rem;
    margin-bottom: 2rem;
  }
  .btn {
    display: inline-block;
    padding: 0.9rem 2.5rem;
    font-size: 1.1rem;
    font-weight: 600;
    color: #fff;
    background: #238636;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s;
  }
  .btn:hover { background: #2ea043; }
  .btn:disabled { background: #21262d; color: #484f58; cursor: wait; }
  .spinner {
    display: none;
    margin: 1.5rem auto 0;
    width: 36px;
    height: 36px;
    border: 3px solid #21262d;
    border-top-color: #58a6ff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .status {
    margin-top: 1rem;
    color: #8b949e;
    font-size: 0.9rem;
    min-height: 1.4em;
  }
  .error {
    color: #f85149;
    margin-top: 1rem;
    font-size: 0.9rem;
  }
</style>
</head>
<body>
<div class="container">
  <h1>atopile</h1>
  <p class="tagline">Design electronics with code</p>
  <button class="btn" id="launch" onclick="spawn()">Try atopile</button>
  <div class="spinner" id="spinner"></div>
  <div class="status" id="status"></div>
  <div class="error" id="error"></div>
</div>
<script>
async function spawn() {
  const btn = document.getElementById('launch');
  const spinner = document.getElementById('spinner');
  const status = document.getElementById('status');
  const error = document.getElementById('error');

  btn.disabled = true;
  spinner.style.display = 'block';
  status.textContent = 'Starting your workspace...';
  error.textContent = '';

  try {
    const res = await fetch('/api/spawn', { method: 'POST' });
    if (res.redirected) {
      window.location.href = res.url;
      return;
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Spawn failed');
    // Should have been redirected; fallback reload
    window.location.reload();
  } catch (err) {
    spinner.style.display = 'none';
    error.textContent = err.message;
    btn.disabled = false;
  }
}
</script>
</body>
</html>`;

// ---------------------------------------------------------------------------
// HTTP server
// ---------------------------------------------------------------------------

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const cookies = parseCookies(req.headers.cookie);
  const machineId = verifyCookie(cookies.session);

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
