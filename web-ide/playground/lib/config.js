// Playground configuration — all env var constants in one place.

const crypto = require("node:crypto");

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
const POOL_SIZE = parseInt(process.env.POOL_SIZE || "1", 10);
const POOL_CHECK_INTERVAL_MS = 30 * 1000; // check pool every 30s

// Derive HMAC secret from FLY_API_TOKEN so all spawner instances share it.
// If no token, fall back to random (local dev — sessions won't survive restart).
const HMAC_SECRET = FLY_API_TOKEN
  ? crypto.createHash("sha256").update(`playground-hmac:${FLY_API_TOKEN}`).digest()
  : crypto.randomBytes(32);

const MACHINES_API = "https://api.machines.dev";

module.exports = {
  PORT,
  FLY_API_TOKEN,
  WORKSPACE_APP,
  WORKSPACE_IMAGE,
  WORKSPACE_REGION,
  MAX_IDLE_MS,
  MAX_LIFETIME_MS,
  CLEANUP_INTERVAL_MS,
  MACHINE_WAIT_TIMEOUT_S,
  MACHINE_WAIT_RETRIES,
  POOL_SIZE,
  POOL_CHECK_INTERVAL_MS,
  HMAC_SECRET,
  MACHINES_API,
};
