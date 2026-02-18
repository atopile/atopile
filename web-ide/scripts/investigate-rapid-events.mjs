#!/usr/bin/env node
/**
 * Simulate rapid BuildsChanged WebSocket events and observe the effect.
 *
 * Connects to the web IDE, waits for WebSocket connection, then injects
 * rapid BuildsChanged events via the WebSocket proxy to simulate what happens
 * during a multi-stage build. Monitors console for errors.
 *
 * Usage:
 *   node web-ide/scripts/investigate-rapid-events.mjs [url] [--headed] [--timeout=120000]
 */

import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(resolve(__dirname, '../../src/ui-server/') + '/');
const puppeteer = require('puppeteer');
const WebSocket = require('ws');

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

const TARGET_URL = positional[0] || 'https://127.0.0.1:3443/?folder=/home/openvscode-server/workspace';
const HEADLESS = !flags.headed;
const ARTIFACTS_DIR = resolve(__dirname, '../artifacts');
mkdirSync(ARTIFACTS_DIR, { recursive: true });

function ts() { return new Date().toISOString(); }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  console.log('\n=== Rapid BuildsChanged Event Investigation ===\n');

  // 1. Connect directly to backend WS to send fake events
  console.log('Step 1: Connecting to backend WebSocket...');
  const backendWs = new WebSocket('wss://127.0.0.1:3443/ws/state', {
    rejectUnauthorized: false,
  });

  await new Promise((resolve, reject) => {
    backendWs.on('open', resolve);
    backendWs.on('error', (e) => reject(new Error(`WS connect failed: ${e.message}`)));
    setTimeout(() => reject(new Error('WS connect timeout')), 10000);
  });
  console.log('  Backend WS connected');

  // 2. Launch browser
  console.log('Step 2: Launching browser...');
  const browser = await puppeteer.launch({
    headless: HEADLESS,
    ignoreHTTPSErrors: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--ignore-certificate-errors'],
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(90000);

  // Collect all console output
  const allLogs = [];
  const errorLogs = [];
  const buildLogs = [];

  page.on('console', (msg) => {
    const entry = { ts: ts(), type: msg.type(), text: msg.text(), source: 'main' };
    allLogs.push(entry);
    if (msg.type() === 'error' || msg.text().includes('Error') || msg.text().includes('error')) {
      errorLogs.push(entry);
    }
    if (msg.text().includes('refresh') || msg.text().includes('builds') || msg.text().includes('Builds')) {
      buildLogs.push(entry);
    }
  });

  page.on('pageerror', (err) => {
    errorLogs.push({ ts: ts(), type: 'pageerror', text: err.message, source: 'main' });
  });

  // Auto-attach to webview iframes
  const cdp = await page.createCDPSession();
  await cdp.send('Network.enable');

  const failedRequests = [];
  const buildsRequests = [];

  page.on('requestfailed', (req) => {
    failedRequests.push({ ts: ts(), url: req.url(), failure: req.failure()?.errorText });
  });

  page.on('request', (req) => {
    if (req.url().includes('builds/active') || req.url().includes('builds/history')) {
      buildsRequests.push({ ts: ts(), url: req.url() });
    }
  });

  const attachedSessions = new Set();
  function instrumentChild(session, label) {
    if (attachedSessions.has(session)) return;
    attachedSessions.add(session);
    session.send('Network.enable').catch(() => {});
    session.send('Runtime.enable').catch(() => {});
    session.on('Runtime.consoleAPICalled', (evt) => {
      const text = evt.args.map((a) => a.value ?? a.description ?? '').join(' ');
      const entry = { ts: ts(), type: evt.type, text, source: label };
      allLogs.push(entry);
      if (evt.type === 'error' || text.includes('Error') || text.includes('error')) {
        errorLogs.push(entry);
      }
      if (text.includes('refresh') || text.includes('builds') || text.includes('Builds')) {
        buildLogs.push(entry);
        console.log(`  [BUILD:${label.slice(0,20)}] ${text.slice(0, 150)}`);
      }
    });
    session.on('Runtime.exceptionThrown', (evt) => {
      const text = evt.exceptionDetails?.text ?? evt.exceptionDetails?.exception?.description ?? '';
      errorLogs.push({ ts: ts(), type: 'exception', text, source: label });
    });
  }

  cdp.on('Target.attachedToTarget', (evt) => {
    try {
      const child = cdp.connection()?.session(evt.sessionId);
      if (child) instrumentChild(child, `${evt.targetInfo.type}:${evt.targetInfo.url.slice(0, 60)}`);
    } catch {}
  });
  await cdp.send('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: false, flatten: true }).catch(() => {});
  browser.on('targetcreated', async (target) => {
    try {
      const session = await target.createCDPSession();
      instrumentChild(session, `target:${target.type()}:${target.url().slice(0, 60)}`);
    } catch {}
  });

  // 3. Load page and wait for connection
  console.log('Step 3: Loading web IDE...');
  await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForSelector('.monaco-workbench', { timeout: 30000 });

  try {
    const atoBarItem = await page.waitForSelector('.action-item a[aria-label="atopile"]', { timeout: 15000 });
    if (atoBarItem) await atoBarItem.click();
  } catch {}

  console.log('Step 4: Waiting for backend connection...');
  try {
    await page.waitForFunction(() => {
      const items = document.querySelectorAll('.statusbar-item');
      for (const item of items) {
        if (/ato:\s*\d+/.test(item.textContent || '')) return true;
      }
      return false;
    }, { timeout: 60000 });
    console.log('  Connected!');
  } catch {
    console.log('  WARNING: Backend connection not confirmed');
  }

  // Wait a moment for everything to settle
  await sleep(3000);

  // 4. Clear counters
  const preErrorCount = errorLogs.length;
  const preBuildLogCount = buildLogs.length;
  const preFailedCount = failedRequests.length;

  // 5. Send rapid BuildsChanged events (simulating a multi-stage build)
  console.log('\nStep 5: Sending 15 rapid BuildsChanged events over 3 seconds...');
  const eventPayload = JSON.stringify({
    type: 'event',
    event: 'BuildsChanged',
    data: {},
  });

  for (let i = 0; i < 15; i++) {
    backendWs.send(eventPayload);
    // ~200ms apart simulates rapid build stage transitions
    await sleep(200);
    process.stdout.write(`\r  Sent ${i + 1}/15 events`);
  }
  console.log('');

  // 6. Wait for all requests to complete
  console.log('\nStep 6: Waiting 20 seconds for requests to settle...');
  for (let i = 0; i < 20; i++) {
    await sleep(1000);
    const newErrors = errorLogs.length - preErrorCount;
    const newBuildLogs = buildLogs.length - preBuildLogCount;
    const newFailedReqs = failedRequests.length - preFailedCount;
    process.stdout.write(`\r  ${i + 1}s | Errors: ${newErrors} | Build logs: ${newBuildLogs} | Failed reqs: ${newFailedReqs}   `);
  }
  console.log('');

  await page.screenshot({ path: resolve(ARTIFACTS_DIR, 'rapid-events-result.png'), fullPage: true });

  // 7. Report
  const newErrors = errorLogs.slice(preErrorCount);
  const newBuildLogs = buildLogs.slice(preBuildLogCount);
  const newFailedReqs = failedRequests.slice(preFailedCount);

  console.log('\n=== RESULTS ===');
  console.log(`Events sent:                    15`);
  console.log(`New errors during test:         ${newErrors.length}`);
  console.log(`New build-related logs:         ${newBuildLogs.length}`);
  console.log(`New failed requests:            ${newFailedReqs.length}`);
  console.log(`Total builds/* reqs seen (CDP): ${buildsRequests.length}`);

  if (newBuildLogs.length > 0) {
    console.log('\n--- Build Logs ---');
    for (const log of newBuildLogs) {
      console.log(`  [${log.ts}] [${log.source.slice(0,30)}] ${log.text.slice(0, 250)}`);
    }
  }

  if (newErrors.length > 0) {
    console.log('\n--- Errors ---');
    for (const err of newErrors) {
      console.log(`  [${err.ts}] [${err.source.slice(0,30)}] ${err.text.slice(0, 250)}`);
    }
  }

  if (newFailedReqs.length > 0) {
    console.log('\n--- Failed Requests ---');
    for (const req of newFailedReqs) {
      console.log(`  [${req.ts}] ${req.url.slice(0, 150)} - ${req.failure}`);
    }
  }

  // Write report
  const report = {
    timestamp: ts(),
    summary: {
      eventsSent: 15,
      newErrors: newErrors.length,
      newBuildLogs: newBuildLogs.length,
      newFailedRequests: newFailedReqs.length,
    },
    newErrors,
    newBuildLogs,
    newFailedReqs,
    allBuildLogs: buildLogs,
  };
  const reportPath = resolve(ARTIFACTS_DIR, 'rapid-events-investigation.json');
  writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`\nReport: ${reportPath}`);

  backendWs.close();
  await browser.close();
  process.exit(newErrors.length > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(2);
});
