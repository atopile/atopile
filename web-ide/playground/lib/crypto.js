// Cookie signing, verification, and HTTP helpers.

const crypto = require("node:crypto");
const { HMAC_SECRET } = require("./config");

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

module.exports = {
  signCookie,
  verifyCookie,
  parseCookies,
  clearSessionCookie,
  setSessionCookie,
  json,
};
