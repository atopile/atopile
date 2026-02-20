// Fly Machines API client — create, wait, list, get, destroy, stop.

const https = require("node:https");
const fs = require("node:fs");
const path = require("node:path");
const {
  FLY_API_TOKEN,
  WORKSPACE_APP,
  WORKSPACE_IMAGE,
  WORKSPACE_REGION,
  MACHINES_API,
  MACHINE_WAIT_TIMEOUT_S,
  MACHINE_WAIT_RETRIES,
} = require("./config");

function machinesRequest(method, reqPath, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(reqPath, MACHINES_API);
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

// Build Caddyfile from the shared scripts/Caddyfile + Fly-specific HTTP listener.
// Fly terminates TLS at the edge and forwards plain HTTP to internal_port.
// The shared Caddyfile is copied into the container at build time (see Dockerfile).
const SHARED_CADDYFILE_PATH = path.join(__dirname, "..", "Caddyfile");
const SHARED_CADDYFILE = fs.readFileSync(SHARED_CADDYFILE_PATH, "utf8");
const CADDYFILE =
  SHARED_CADDYFILE +
  "\n# Plain HTTP for Fly proxy (internal_port)\n" +
  "http://:3080 {\n\timport atopile_proxy\n}\n";

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

module.exports = {
  machinesRequest,
  machineConfig,
  createMachine,
  waitForMachine,
  listMachines,
  getMachine,
  destroyMachine,
  stopMachine,
};
