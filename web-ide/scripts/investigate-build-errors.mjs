#!/usr/bin/env node
/**
 * Investigate NetworkError spam during builds.
 *
 * Connects to the running web IDE, waits for WS connection, triggers a build,
 * and captures all console logs + errors related to "refreshBuilds", "NetworkError",
 * "builds/active", "builds/history", and "NS_ERROR".
 *
 * Usage:
 *   node web-ide/scripts/investigate-build-errors.mjs [url] [--headed] [--timeout=120000]
 */

import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(resolve(__dirname, '../../src/ui-server/') + '/');
const puppeteer = require('puppeteer');

// CLI args
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
const GLOBAL_TIMEOUT = parseInt(flags.timeout ?? '120000', 10);
const HEADLESS = !flags.headed;

const ARTIFACTS_DIR = resolve(__dirname, '../artifacts');
mkdirSync(ARTIFACTS_DIR, { recursive: true });

function ts() { return new Date().toISOString(); }

// Collect ALL console logs
const allConsoleLogs = [];
const allPageErrors = [];
const networkErrorLogs = [];
const buildRelatedLogs = [];

async function main() {
  console.log(`\n=== Build Error Investigation ===`);
  console.log(`  URL:     ${TARGET_URL}`);
  console.log(`  Timeout: ${GLOBAL_TIMEOUT}ms`);
  console.log(`  Mode:    ${HEADLESS ? 'headless' : 'headed'}\n`);

  const browser = await puppeteer.launch({
    headless: HEADLESS,
    ignoreHTTPSErrors: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--ignore-certificate-errors',
    ],
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(GLOBAL_TIMEOUT);

  // Instrument console
  page.on('console', (msg) => {
    const entry = { ts: ts(), type: msg.type(), text: msg.text(), source: 'main' };
    allConsoleLogs.push(entry);

    const t = msg.text();
    if (t.includes('NetworkError') || t.includes('NS_ERROR') || t.includes('interception')) {
      networkErrorLogs.push(entry);
      console.log(`  [NET-ERR] ${t.slice(0, 200)}`);
    }
    if (t.includes('refreshBuilds') || t.includes('builds/active') || t.includes('builds/history') || t.includes('BuildsChanged') || t.includes('debouncedRefresh')) {
      buildRelatedLogs.push(entry);
    }
  });

  page.on('pageerror', (err) => {
    const entry = { ts: ts(), message: err.message, stack: err.stack };
    allPageErrors.push(entry);
    if (err.message.includes('NetworkError') || err.message.includes('NS_ERROR')) {
      networkErrorLogs.push({ ts: ts(), type: 'pageerror', text: err.message, source: 'main' });
      console.log(`  [PAGE-ERR] ${err.message.slice(0, 200)}`);
    }
  });

  // CDP: also instrument child targets (webview iframes)
  const cdp = await page.createCDPSession();
  await cdp.send('Network.enable');

  // Track HTTP requests to builds endpoints
  const buildsRequests = [];
  const failedRequests = [];

  page.on('request', (req) => {
    const url = req.url();
    if (url.includes('builds/active') || url.includes('builds/history') || url.includes('builds/queue')) {
      buildsRequests.push({ ts: ts(), method: req.method(), url });
    }
  });

  page.on('requestfailed', (req) => {
    failedRequests.push({ ts: ts(), url: req.url(), failure: req.failure()?.errorText });
    if (req.url().includes('builds')) {
      console.log(`  [REQ-FAIL] ${req.url()} - ${req.failure()?.errorText}`);
    }
  });

  // Auto-attach to child targets for webview console capture
  const attachedSessions = new Set();
  function instrumentChild(session, label) {
    if (attachedSessions.has(session)) return;
    attachedSessions.add(session);
    session.send('Network.enable').catch(() => {});
    session.send('Runtime.enable').catch(() => {});
    session.on('Runtime.consoleAPICalled', (evt) => {
      const text = evt.args.map((a) => a.value ?? a.description ?? '').join(' ');
      const entry = { ts: ts(), type: evt.type, text, source: label };
      allConsoleLogs.push(entry);

      if (text.includes('NetworkError') || text.includes('NS_ERROR') || text.includes('interception')) {
        networkErrorLogs.push(entry);
        console.log(`  [NET-ERR:${label}] ${text.slice(0, 200)}`);
      }
      if (text.includes('refreshBuilds') || text.includes('builds/active') || text.includes('builds/history') || text.includes('BuildsChanged') || text.includes('debouncedRefresh') || text.includes('Failed to refresh builds')) {
        buildRelatedLogs.push(entry);
        console.log(`  [BUILD:${label}] ${text.slice(0, 200)}`);
      }
    });
    session.on('Runtime.exceptionThrown', (evt) => {
      const text = evt.exceptionDetails?.text ?? evt.exceptionDetails?.exception?.description ?? '';
      if (text.includes('NetworkError') || text.includes('NS_ERROR')) {
        networkErrorLogs.push({ ts: ts(), type: 'exception', text, source: label });
        console.log(`  [EXCEPTION:${label}] ${text.slice(0, 200)}`);
      }
    });
  }

  cdp.on('Target.attachedToTarget', (evt) => {
    try {
      const child = cdp.connection()?.session(evt.sessionId);
      if (child) {
        instrumentChild(child, `${evt.targetInfo.type}:${evt.targetInfo.url.slice(0, 60)}`);
      }
    } catch {}
  });
  await cdp.send('Target.setAutoAttach', {
    autoAttach: true,
    waitForDebuggerOnStart: false,
    flatten: true,
  }).catch(() => {});

  browser.on('targetcreated', async (target) => {
    try {
      const session = await target.createCDPSession();
      instrumentChild(session, `target:${target.type()}:${target.url().slice(0, 60)}`);
    } catch {}
  });

  // 1. Load page
  console.log('Step 1: Loading web IDE...');
  await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  console.log('  Page loaded');

  // 2. Wait for workbench
  console.log('Step 2: Waiting for workbench...');
  await page.waitForSelector('.monaco-workbench', { timeout: 30_000 });
  console.log('  Workbench rendered');

  // 3. Click atopile sidebar
  console.log('Step 3: Opening atopile sidebar...');
  try {
    const atoBarItem = await page.waitForSelector(
      '.action-item a[aria-label="atopile"]',
      { timeout: 15_000 }
    );
    if (atoBarItem) {
      await atoBarItem.click();
      console.log('  Clicked atopile sidebar');
    }
  } catch {
    console.log('  Sidebar icon not found (may already be open)');
  }

  // 4. Wait for backend connection
  console.log('Step 4: Waiting for backend connection...');
  try {
    await page.waitForFunction(
      () => {
        const items = document.querySelectorAll('.statusbar-item');
        for (const item of items) {
          if (/ato:\s*\d+/.test(item.textContent || '')) return true;
        }
        return false;
      },
      { timeout: 60_000 }
    );
    const statusText = await page.evaluate(() => {
      const items = document.querySelectorAll('.statusbar-item');
      for (const item of items) {
        const t = item.textContent || '';
        if (t.includes('ato:')) return t.trim();
      }
      return '';
    });
    console.log(`  Connected: ${statusText}`);
  } catch {
    console.log('  WARNING: Backend connection not detected within 60s');
  }

  await page.screenshot({ path: resolve(ARTIFACTS_DIR, 'build-investigate-01-connected.png'), fullPage: true });

  // 5. Clear counters before build
  const preBuildsErrorCount = networkErrorLogs.length;
  const preBuildRequestCount = buildsRequests.length;
  const preBuildRelatedCount = buildRelatedLogs.length;

  // 6. Trigger build - look for build button in sidebar
  console.log('\nStep 5: Triggering build...');
  // Try to find and click a build button within the sidebar webview
  // The sidebar runs in an iframe, so we need to find it

  // First try: look for build button in iframes
  let buildTriggered = false;
  const frames = page.frames();
  console.log(`  Found ${frames.length} frames`);
  for (const frame of frames) {
    const url = frame.url();
    if (url.includes('webview') || url.includes('sidebar')) {
      console.log(`  Checking frame: ${url.slice(0, 100)}`);
      try {
        // Look for build button
        const buildBtn = await frame.$('button:has-text("Build"), [data-testid="build-button"], button.build-button');
        if (buildBtn) {
          await buildBtn.click();
          buildTriggered = true;
          console.log('  Build button clicked in iframe!');
          break;
        }
      } catch (e) {
        // frame might not be accessible
      }
    }
  }

  if (!buildTriggered) {
    // Try using keyboard shortcut or command palette
    console.log('  Trying command palette...');
    try {
      // Open command palette
      await page.keyboard.down('Control');
      await page.keyboard.down('Shift');
      await page.keyboard.press('KeyP');
      await page.keyboard.up('Shift');
      await page.keyboard.up('Control');
      await new Promise(r => setTimeout(r, 1000));

      // Type build command
      await page.keyboard.type('atopile: Build', { delay: 50 });
      await new Promise(r => setTimeout(r, 1500));

      // Press enter to execute
      await page.keyboard.press('Enter');
      buildTriggered = true;
      console.log('  Build triggered via command palette');
    } catch (e) {
      console.log(`  Command palette approach failed: ${e.message}`);
    }
  }

  if (!buildTriggered) {
    console.log('  WARNING: Could not trigger build automatically');
    console.log('  Please trigger a build manually in the web IDE');
    console.log('  Waiting 60s for manual build trigger...');
  }

  // 7. Monitor for 45 seconds during/after build
  console.log('\nStep 6: Monitoring for 45 seconds during build...');
  const monitorStart = Date.now();
  const MONITOR_DURATION = 45_000;

  while (Date.now() - monitorStart < MONITOR_DURATION) {
    const elapsed = Math.round((Date.now() - monitorStart) / 1000);
    const newErrors = networkErrorLogs.length - preBuildsErrorCount;
    const newBuildRequests = buildsRequests.length - preBuildRequestCount;
    const newBuildLogs = buildRelatedLogs.length - preBuildRelatedCount;

    if (elapsed % 5 === 0) {
      process.stdout.write(`\r  ${elapsed}s elapsed | NetworkErrors: ${newErrors} | Build HTTP reqs: ${newBuildRequests} | Build logs: ${newBuildLogs}   `);
    }
    await new Promise(r => setTimeout(r, 1000));
  }
  console.log('');

  await page.screenshot({ path: resolve(ARTIFACTS_DIR, 'build-investigate-02-after-build.png'), fullPage: true });

  // 8. Report
  const postNetErrors = networkErrorLogs.length - preBuildsErrorCount;
  const postBuildRequests = buildsRequests.length - preBuildRequestCount;
  const postBuildLogs = buildRelatedLogs.length - preBuildRelatedCount;

  console.log('\n=== RESULTS ===');
  console.log(`NetworkError/NS_ERROR entries during build: ${postNetErrors}`);
  console.log(`builds/* HTTP requests during build:        ${postBuildRequests}`);
  console.log(`Build-related console logs during build:    ${postBuildLogs}`);
  console.log(`Total console errors (all time):            ${allConsoleLogs.filter(l => l.type === 'error').length}`);
  console.log(`Total page errors (all time):               ${allPageErrors.length}`);
  console.log(`Total failed requests (all time):           ${failedRequests.length}`);

  if (postNetErrors > 0) {
    console.log('\n--- NetworkError Details ---');
    for (const err of networkErrorLogs.slice(preBuildsErrorCount)) {
      console.log(`  [${err.ts}] [${err.source}] ${err.text.slice(0, 300)}`);
    }
  }

  if (postBuildLogs > 0) {
    console.log('\n--- Build-Related Logs ---');
    for (const log of buildRelatedLogs.slice(preBuildRelatedCount)) {
      console.log(`  [${log.ts}] [${log.source}] ${log.text.slice(0, 300)}`);
    }
  }

  if (failedRequests.length > 0) {
    console.log('\n--- Failed Requests ---');
    for (const req of failedRequests) {
      console.log(`  [${req.ts}] ${req.url.slice(0, 150)} - ${req.failure}`);
    }
  }

  // Also dump all error console logs
  const errorLogs = allConsoleLogs.filter(l => l.type === 'error');
  if (errorLogs.length > 0) {
    console.log(`\n--- All Console Errors (${errorLogs.length}) ---`);
    for (const log of errorLogs.slice(0, 50)) {
      console.log(`  [${log.ts}] [${log.source}] ${log.text.slice(0, 300)}`);
    }
  }

  // Write full report
  const report = {
    timestamp: ts(),
    url: TARGET_URL,
    summary: {
      networkErrors: postNetErrors,
      buildsRequests: postBuildRequests,
      buildRelatedLogs: postBuildLogs,
      totalConsoleErrors: errorLogs.length,
      totalPageErrors: allPageErrors.length,
      totalFailedRequests: failedRequests.length,
    },
    networkErrorLogs,
    buildRelatedLogs,
    buildsRequests,
    failedRequests,
    allConsoleErrors: errorLogs,
    allPageErrors,
    allConsoleLogs: allConsoleLogs.slice(-500), // last 500 for context
  };

  const reportPath = resolve(ARTIFACTS_DIR, 'build-investigation.json');
  writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`\nFull report: ${reportPath}`);

  await browser.close();

  process.exit(postNetErrors > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(2);
});
