#!/usr/bin/env node
/**
 * Web IDE Browser Validation Script
 *
 * Launches headless Chrome against a running web IDE instance, instruments
 * the page for console logs, network traffic, and WebSocket frames, then
 * runs a series of validation checks and produces a report.
 *
 * Usage:
 *   node web-ide/scripts/validate.mjs [url] [--timeout=60000] [--headed]
 *
 * Default: http://127.0.0.1:3000, headless, 60s global timeout.
 *
 * Requires the web IDE container to be running already.
 *
 * Architecture note:
 *   The sidebar webview runs inside cross-origin iframes (vscode-cdn.net)
 *   whose network traffic is tunneled through VS Code's internal port
 *   forwarding — invisible to CDP. WebSocket checks therefore rely on
 *   observing the status bar text transition from "ato: Connecting..." to
 *   "ato: <port>" (which the extension sets when the webview reports a
 *   successful WebSocket connection via postMessage).
 */

import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// ---------------------------------------------------------------------------
// Resolve puppeteer from ui-server's node_modules
// ---------------------------------------------------------------------------
const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(resolve(__dirname, '../../src/ui-server/') + '/');
const puppeteer = require('puppeteer');

// ---------------------------------------------------------------------------
// CLI args
// ---------------------------------------------------------------------------
const args = process.argv.slice(2);
const flags = {};
const positional = [];
for (const arg of args) {
  if (arg.startsWith('--')) {
    const [key, val] = arg.slice(2).split('=');
    flags[key] = val ?? true;
  } else {
    positional.push(arg);
  }
}

const TARGET_URL = positional[0] || 'http://127.0.0.1:3000';
const GLOBAL_TIMEOUT = parseInt(flags.timeout ?? '60000', 10);
const HEADLESS = !flags.headed;

// ---------------------------------------------------------------------------
// Artifacts directory
// ---------------------------------------------------------------------------
const ARTIFACTS_DIR = resolve(__dirname, '../artifacts');
mkdirSync(ARTIFACTS_DIR, { recursive: true });

// ---------------------------------------------------------------------------
// Telemetry collectors
// ---------------------------------------------------------------------------
const telemetry = {
  consoleLogs: [],
  pageErrors: [],
  requests: [],
  responses: [],
  wsCreated: [],
  wsSent: [],
  wsReceived: [],
  wsClosed: [],
  containerLogs: null,
  screenshots: [],
};

function ts() {
  return new Date().toISOString();
}

// ---------------------------------------------------------------------------
// Checks definition
// ---------------------------------------------------------------------------
const checks = [
  { id: 'page_load', timeout: 30_000 },
  { id: 'workbench_render', timeout: 30_000 },
  { id: 'atopile_status_bar', timeout: 45_000 },
  { id: 'backend_websocket', timeout: 60_000 },
  { id: 'websocket_message', timeout: 60_000 },
  { id: 'no_csp_errors', timeout: 0 },        // passive
  { id: 'no_critical_errors', timeout: 0 },    // passive
];

const results = {};

function pass(id, detail) {
  results[id] = { status: 'PASS', detail: detail || '', ts: ts() };
  console.log(`  ✓ ${id}${detail ? ': ' + detail : ''}`);
}

function fail(id, detail) {
  results[id] = { status: 'FAIL', detail: detail || '', ts: ts() };
  console.log(`  ✗ ${id}${detail ? ': ' + detail : ''}`);
}

async function screenshot(page, label) {
  const filename = `${label}-${Date.now()}.png`;
  const filepath = resolve(ARTIFACTS_DIR, filename);
  await page.screenshot({ path: filepath, fullPage: true });
  telemetry.screenshots.push({ label, path: filepath, ts: ts() });
}

// ---------------------------------------------------------------------------
// Container logs (best-effort)
// ---------------------------------------------------------------------------
function collectContainerLogs() {
  for (const cmd of [
    'podman logs --tail=500 atopile-web-ide 2>&1',
    'docker logs --tail=500 atopile-web-ide 2>&1',
  ]) {
    try {
      telemetry.containerLogs = execSync(cmd, { timeout: 5000, encoding: 'utf-8' });
      return;
    } catch {
      // Try next
    }
  }
  telemetry.containerLogs = '(container logs unavailable)';
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log(`\nWeb IDE Validation`);
  console.log(`  URL:     ${TARGET_URL}`);
  console.log(`  Timeout: ${GLOBAL_TIMEOUT}ms`);
  console.log(`  Mode:    ${HEADLESS ? 'headless' : 'headed'}\n`);

  collectContainerLogs();

  const browser = await puppeteer.launch({
    headless: HEADLESS,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
    ],
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(GLOBAL_TIMEOUT);

  // ------- Instrument -------

  page.on('console', (msg) => {
    telemetry.consoleLogs.push({
      ts: ts(),
      type: msg.type(),
      text: msg.text(),
      location: msg.location(),
      source: 'main',
    });
  });

  page.on('pageerror', (err) => {
    telemetry.pageErrors.push({ ts: ts(), message: err.message, stack: err.stack });
  });

  page.on('request', (req) => {
    telemetry.requests.push({ ts: ts(), method: req.method(), url: req.url() });
  });
  page.on('response', (res) => {
    telemetry.responses.push({ ts: ts(), status: res.status(), url: res.url() });
  });

  // WebSocket tracking via CDP
  const wsConnections = new Map();
  let stateWsRequestId = null;
  let gotWsMessage = false;

  function attachWsListeners(cdpSession, label) {
    cdpSession.on('Network.webSocketCreated', (evt) => {
      telemetry.wsCreated.push({ ts: ts(), requestId: evt.requestId, url: evt.url, target: label });
      wsConnections.set(evt.requestId, evt.url);
      if (evt.url.includes('/ws/state')) {
        stateWsRequestId = evt.requestId;
      }
    });

    cdpSession.on('Network.webSocketFrameSent', (evt) => {
      const payload = evt.response?.payloadData;
      telemetry.wsSent.push({
        ts: ts(), requestId: evt.requestId,
        url: wsConnections.get(evt.requestId),
        payload: typeof payload === 'string' ? payload.slice(0, 500) : '(binary)',
        target: label,
      });
    });

    cdpSession.on('Network.webSocketFrameReceived', (evt) => {
      const payload = evt.response?.payloadData;
      telemetry.wsReceived.push({
        ts: ts(), requestId: evt.requestId,
        url: wsConnections.get(evt.requestId),
        payload: typeof payload === 'string' ? payload.slice(0, 500) : '(binary)',
        target: label,
      });
      if (evt.requestId === stateWsRequestId) {
        gotWsMessage = true;
      }
    });

    cdpSession.on('Network.webSocketClosed', (evt) => {
      telemetry.wsClosed.push({
        ts: ts(), requestId: evt.requestId,
        url: wsConnections.get(evt.requestId),
        target: label,
      });
    });
  }

  // Instrument main page
  const cdp = await page.createCDPSession();
  await cdp.send('Network.enable');
  attachWsListeners(cdp, 'main');

  // Try to auto-attach to child frames (webview iframes)
  // Note: in OpenVSCode Server, the webview WS goes through VS Code's
  // internal port tunnel and may not be visible to CDP even with auto-attach.
  const attachedSessions = new Set();
  function instrumentChildSession(session, label) {
    if (attachedSessions.has(session)) return;
    attachedSessions.add(session);
    session.send('Network.enable').catch(() => {});
    attachWsListeners(session, label);
    session.send('Runtime.enable').catch(() => {});
    session.on('Runtime.consoleAPICalled', (evt) => {
      const text = evt.args.map((a) => a.value ?? a.description ?? '').join(' ');
      telemetry.consoleLogs.push({
        ts: ts(), type: evt.type, text,
        location: evt.stackTrace?.callFrames?.[0] || {},
        source: label,
      });
    });
  }

  cdp.on('Target.attachedToTarget', (evt) => {
    try {
      const child = cdp.connection()?.session(evt.sessionId);
      if (child) {
        const label = `${evt.targetInfo.type}:${evt.targetInfo.url.slice(0, 80)}`;
        instrumentChildSession(child, label);
      }
    } catch {}
  });
  await cdp.send('Target.setAutoAttach', {
    autoAttach: true,
    waitForDebuggerOnStart: false,
    flatten: true,
  }).catch(() => {});

  // Also instrument browser-level targets
  browser.on('targetcreated', async (target) => {
    try {
      const session = await target.createCDPSession();
      instrumentChildSession(session, `target:${target.type()}:${target.url().slice(0, 60)}`);
    } catch {}
  });

  // ------- Check 1: page_load -------
  console.log('Running checks...');
  try {
    const response = await page.goto(TARGET_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 30_000,
    });
    if (response && response.status() === 200) {
      pass('page_load', `HTTP ${response.status()}`);
    } else {
      fail('page_load', `HTTP ${response ? response.status() : 'no response'}`);
    }
  } catch (err) {
    fail('page_load', err.message);
  }

  await screenshot(page, '01-page-load');

  // ------- Check 2: workbench_render -------
  try {
    await page.waitForSelector('.monaco-workbench', { timeout: 30_000 });
    pass('workbench_render', '.monaco-workbench found');
  } catch {
    fail('workbench_render', '.monaco-workbench not found within 30s');
  }

  await screenshot(page, '02-workbench-render');

  // ------- Open atopile sidebar (lazy-loaded, needs click to trigger WebSocket) -------
  try {
    const atoBarItem = await page.waitForSelector(
      '.action-item a[aria-label="atopile"]',
      { timeout: 15_000 }
    );
    if (atoBarItem) {
      await atoBarItem.click();
      console.log('  → Clicked atopile activity bar icon');
      // Give the sidebar a moment to start loading
      await new Promise((r) => setTimeout(r, 2000));
    }
  } catch {
    console.log('  → atopile activity bar icon not found (sidebar may already be open)');
  }

  // ------- Check 3: atopile_status_bar -------
  try {
    await page.waitForFunction(
      () => {
        const items = document.querySelectorAll('.statusbar-item');
        for (const item of items) {
          if (item.textContent && item.textContent.includes('ato:')) return true;
        }
        return false;
      },
      { timeout: 45_000 }
    );
    pass('atopile_status_bar', 'status bar item containing "ato:" found');
  } catch {
    fail('atopile_status_bar', 'no status bar item with "ato:" found within 45s');
  }

  await screenshot(page, '03-status-bar');

  // ------- Check 4 & 5: backend_websocket + websocket_message -------
  // Detection strategy:
  //  1) CDP: if auto-attach captured the /ws/state WebSocket directly
  //  2) Status bar: poll for "ato: <port>" which means the extension
  //     received a connectionStatus={isConnected:true} from the webview,
  //     confirming the WS is open and messages have flowed.
  let wsCheckPassed = stateWsRequestId !== null;
  let wsMessagePassed = gotWsMessage;
  let wsDetail = wsCheckPassed ? `CDP: WebSocket to ${wsConnections.get(stateWsRequestId)}` : '';
  let wsMsgDetail = wsMessagePassed ? 'CDP: received frame on /ws/state' : '';

  if (!wsCheckPassed || !wsMessagePassed) {
    const deadline = Date.now() + 60_000;
    while (Date.now() < deadline && (!wsCheckPassed || !wsMessagePassed)) {
      // CDP may have caught it since last check
      if (!wsCheckPassed && stateWsRequestId) {
        wsCheckPassed = true;
        wsDetail = `CDP: WebSocket to ${wsConnections.get(stateWsRequestId)}`;
      }
      if (!wsMessagePassed && gotWsMessage) {
        wsMessagePassed = true;
        wsMsgDetail = 'CDP: received frame on /ws/state';
      }

      // Poll status bar: "ato: 8501" = connected, vs "ato: Connecting..."
      if (!wsCheckPassed) {
        const statusText = await page.evaluate(() => {
          const items = document.querySelectorAll('.statusbar-item');
          for (const item of items) {
            const text = item.textContent || '';
            if (text.includes('ato:')) return text;
          }
          return '';
        }).catch(() => '');

        const portMatch = statusText.match(/ato:\s*(\d+)/);
        if (portMatch) {
          wsCheckPassed = true;
          wsDetail = `status bar connected: "${statusText.trim()}" (port ${portMatch[1]})`;
          wsMessagePassed = true;
          wsMsgDetail = `implied by connected status (port ${portMatch[1]})`;
        }
      }

      if (!wsCheckPassed || !wsMessagePassed) {
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
  }

  if (wsCheckPassed) {
    pass('backend_websocket', wsDetail);
  } else {
    fail('backend_websocket', 'no WebSocket to /ws/state detected within 60s');
  }

  if (wsMessagePassed) {
    pass('websocket_message', wsMsgDetail);
  } else {
    fail('websocket_message', 'no WebSocket message on /ws/state within 60s');
  }

  await screenshot(page, '04-websocket-connected');

  // ------- Check 6: no_csp_errors (passive) -------
  const cspErrors = telemetry.consoleLogs.filter(
    (log) => log.type === 'error' && log.text.includes('Content Security Policy')
  );
  if (cspErrors.length === 0) {
    pass('no_csp_errors', 'no CSP errors in console');
  } else {
    fail('no_csp_errors', `${cspErrors.length} CSP error(s): ${cspErrors[0].text.slice(0, 120)}`);
  }

  // ------- Check 7: no_critical_errors (passive) -------
  if (telemetry.pageErrors.length === 0) {
    pass('no_critical_errors', 'no uncaught page errors');
  } else {
    const first = telemetry.pageErrors[0];
    fail(
      'no_critical_errors',
      `${telemetry.pageErrors.length} error(s): ${first.message.slice(0, 120)}`
    );
  }

  // ------- Final screenshot -------
  await screenshot(page, '05-final');

  // ------- Key signals summary -------
  console.log('\nKey signals detected:');

  const initLog = telemetry.consoleLogs.find((l) =>
    l.text.includes('[atopile webview] Initializing')
  );
  console.log(`  [atopile webview] Initializing: ${initLog ? 'yes' : 'no'}`);

  const wsConnectedLog = telemetry.consoleLogs.find((l) =>
    l.text.includes('[WS] Connected')
  );
  console.log(`  [WS] Connected:                ${wsConnectedLog ? 'yes' : 'no'}`);

  const backendReadyLog = telemetry.consoleLogs.find((l) =>
    l.text.includes('backend ready')
  );
  console.log(`  backend ready:                 ${backendReadyLog ? 'yes' : 'no'}`);

  const finalStatusBar = await page.evaluate(() => {
    const items = document.querySelectorAll('.statusbar-item');
    for (const item of items) {
      const text = item.textContent || '';
      if (text.includes('ato:')) return text.trim();
    }
    return '(not found)';
  }).catch(() => '(error reading)');
  console.log(`  Status bar text:                ${finalStatusBar}`);

  console.log(`  WebSocket /ws/state (CDP):      ${stateWsRequestId ? 'yes' : 'no'}`);
  console.log(`  WS message received (CDP):      ${gotWsMessage ? 'yes' : 'no'}`);
  console.log(`  Console errors:                 ${telemetry.consoleLogs.filter((l) => l.type === 'error').length}`);
  console.log(`  Page errors:                    ${telemetry.pageErrors.length}`);
  console.log(`  Total HTTP requests:            ${telemetry.requests.length}`);
  console.log(`  Total WS frames (VS Code):      ${telemetry.wsReceived.length}`);

  // ------- Write report -------
  const report = {
    url: TARGET_URL,
    timestamp: ts(),
    results,
    telemetry,
  };

  const reportPath = resolve(ARTIFACTS_DIR, 'validation-logs.json');
  writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`\nReport written to: ${reportPath}`);
  console.log(`Screenshots in:    ${ARTIFACTS_DIR}/`);

  // ------- Summary -------
  const total = checks.length;
  const passed = Object.values(results).filter((r) => r.status === 'PASS').length;
  const failed = total - passed;

  console.log(`\n${'='.repeat(40)}`);
  console.log(`Results: ${passed}/${total} passed, ${failed} failed`);
  console.log(`${'='.repeat(40)}\n`);

  await browser.close();

  process.exit(failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(2);
});
