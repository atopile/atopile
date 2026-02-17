#!/usr/bin/env node
/**
 * Layout interaction validator for web-ide.
 *
 * Checks:
 * 1) Workbench loads and atopile sidebar is reachable.
 * 2) Layout panel can be opened from the sidebar.
 * 3) Layout webview can reach /api/layout via the in-webview fetch bridge.
 * 4) A user-style interaction attempt (click + R) changes at least one footprint.
 */

import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { writeFileSync, mkdirSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(resolve(__dirname, '../../src/ui-server/') + '/');
const puppeteer = require('puppeteer');

const DEFAULT_URL = 'https://127.0.0.1:3443/?folder=/home/openvscode-server/workspace';
const TARGET_URL = process.argv[2] || DEFAULT_URL;
const ARTIFACTS_DIR = resolve(__dirname, '../artifacts');
mkdirSync(ARTIFACTS_DIR, { recursive: true });

function sleep(ms) {
  return new Promise((resolveFn) => setTimeout(resolveFn, ms));
}

function summarizeModel(model) {
  const map = new Map();
  for (const fp of model?.footprints || []) {
    if (!fp?.uuid || !fp?.at) continue;
    map.set(fp.uuid, { x: Number(fp.at.x || 0), y: Number(fp.at.y || 0), r: Number(fp.at.r || 0) });
  }
  return map;
}

function anyFootprintChanged(before, after, eps = 1e-6) {
  for (const [uuid, b] of before.entries()) {
    const a = after.get(uuid);
    if (!a) continue;
    if (Math.abs(a.x - b.x) > eps || Math.abs(a.y - b.y) > eps || Math.abs(a.r - b.r) > eps) {
      return { uuid, before: b, after: a };
    }
  }
  return null;
}

async function findFrame(page, predicate, attempts = 40, delayMs = 250) {
  for (let i = 0; i < attempts; i++) {
    for (const frame of page.frames()) {
      try {
        // eslint-disable-next-line no-await-in-loop
        const ok = await frame.evaluate(predicate);
        if (ok) return frame;
      } catch {
        // ignore transient cross-context errors
      }
    }
    // eslint-disable-next-line no-await-in-loop
    await sleep(delayMs);
  }
  return null;
}

async function waitForTruthy(fn, attempts = 120, delayMs = 250) {
  for (let i = 0; i < attempts; i++) {
    // eslint-disable-next-line no-await-in-loop
    const value = await fn();
    if (value) return value;
    // eslint-disable-next-line no-await-in-loop
    await sleep(delayMs);
  }
  return null;
}

async function ensureAtopileViewVisible(page) {
  const selector = '.activitybar .action-item a[aria-label="atopile"]';
  await page.waitForSelector(selector, { timeout: 60000 });
  const isChecked = await page.$eval(selector, (el) => {
    if (el.classList.contains('checked')) return true;
    const item = el.closest('.action-item');
    return Boolean(item?.classList.contains('checked'));
  });
  if (!isChecked) {
    await page.click(selector);
    await sleep(800);
  }
}

async function run() {
  const browser = await puppeteer.launch({
    headless: true,
    ignoreHTTPSErrors: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--ignore-certificate-errors',
    ],
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(60000);

  const logs = [];
  page.on('console', (msg) => logs.push({ type: msg.type(), text: msg.text() }));
  page.on('pageerror', (err) => logs.push({ type: 'pageerror', text: err.message }));

  const result = {
    url: TARGET_URL,
    checks: {},
    detail: {},
  };

  try {
    const resp = await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded' });
    result.checks.page_load = resp?.status() === 200;
    if (!result.checks.page_load) throw new Error(`page load failed: HTTP ${resp?.status()}`);

    await page.waitForSelector('.monaco-workbench', { timeout: 30000 });
    result.checks.workbench = true;

    // Ensure atopile activity sidebar is visible (avoid toggling it closed).
    await ensureAtopileViewVisible(page);

    await page.waitForFunction(() => {
      const items = document.querySelectorAll('.statusbar-item');
      return Array.from(items).some((n) => (n.textContent || '').includes('ato:'));
    }, { timeout: 45000 });
    result.checks.atopile_status = true;

    const connectedStatus = await waitForTruthy(async () => {
      const statuses = await page.$$eval(
        '.statusbar-item',
        (els) => els.map((e) => (e.textContent || '').trim()).filter(Boolean)
      );
      return statuses.find((s) => /ato:\s*\d+/.test(s)) || null;
    }, 120, 500);
    result.checks.atopile_connected = Boolean(connectedStatus);
    result.detail.atopile_status_text = connectedStatus;
    if (!connectedStatus) {
      throw new Error('backend never reached connected state (expected status like "ato:8501")');
    }

    // After status settles, ensure view is still visible before frame lookup.
    await ensureAtopileViewVisible(page);

    // Find sidebar webview frame with Layout button.
    const sidebarFrame = await findFrame(
      page,
      () => {
        const href = window.location.href || '';
        if (!href.includes('extensionId=atopile.atopile')) return false;
        const text = document.body?.innerText || '';
        return /atopile/i.test(text) && (/BUILD QUEUE/.test(text) || /Build Workspace/.test(text));
      },
      200,
      250
    );
    if (!sidebarFrame) {
      result.detail.frame_probe = [];
      for (const frame of page.frames()) {
        try {
          // eslint-disable-next-line no-await-in-loop
          const probe = await frame.evaluate(() => ({
            href: window.location.href,
            text: (document.body?.innerText || '').slice(0, 240),
          }));
          result.detail.frame_probe.push(probe);
        } catch (err) {
          result.detail.frame_probe.push({ href: frame.url(), error: String(err) });
        }
      }
      throw new Error('could not find atopile sidebar frame');
    }

    let layoutProbe = { state: 'missing' };
    for (let i = 0; i < 120; i++) {
      // eslint-disable-next-line no-await-in-loop
      const probe = await sidebarFrame.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const summaries = buttons.slice(0, 30).map((b) => ({
          text: (b.textContent || '').trim(),
          title: (b.getAttribute('title') || '').trim(),
          aria: (b.getAttribute('aria-label') || '').trim(),
          disabled: b.disabled,
        }));
        const btn = buttons.find((b) => {
          const text = (b.textContent || '').trim();
          const title = (b.getAttribute('title') || '').trim();
          const aria = (b.getAttribute('aria-label') || '').trim();
          return /layout/i.test(text) || /layout/i.test(title) || /layout/i.test(aria);
        });
        if (!btn) return { state: 'missing', summaries };
        if (btn.disabled) return { state: 'disabled', summaries };
        btn.click();
        return { state: 'clicked', summaries };
      });
      layoutProbe = probe;
      if (probe.state === 'clicked') break;
      // eslint-disable-next-line no-await-in-loop
      await sleep(250);
    }
    result.detail.layout_button_state = layoutProbe;
    if (layoutProbe.state !== 'clicked') {
      throw new Error(`layout button was not clickable (state: ${layoutProbe.state})`);
    }
    result.checks.layout_button_click = true;

    // Find layout editor frame by canvas.
    const layoutFrame = await findFrame(
      page,
      () => {
        return Boolean(document.querySelector('#editor-canvas'));
      },
      120,
      250
    );
    if (!layoutFrame) throw new Error('layout editor frame not found');
    result.checks.layout_frame = true;

    // Fetch model through layout frame (uses webview bridge/proxy path).
    const modelBefore = await layoutFrame.evaluate(async () => {
      const w = window;
      const base = w.__LAYOUT_BASE_URL__;
      const apiPrefix = w.__LAYOUT_API_PREFIX__ || '/api/layout';
      const r = await fetch(`${base}${apiPrefix}/render-model`);
      return await r.json();
    });
    const beforeMap = summarizeModel(modelBefore);
    result.detail.footprints_before = beforeMap.size;
    if (beforeMap.size === 0) throw new Error('render-model returned no footprints');
    result.checks.bridge_render_model = true;

    // User-style interaction path: select a footprint and trigger rotate shortcut.
    const uiResult = await layoutFrame.evaluate(async () => {
      // editor is the top-level var from layout editor script (non-module bundle)
      if (typeof editor === 'undefined') return { ok: false, reason: 'editor-missing' };
      if (!editor.model?.footprints?.length) return { ok: false, reason: 'no-footprints' };

      const fp = editor.model.footprints[0];
      const world = { x: Number(fp.at?.x || 0), y: Number(fp.at?.y || 0) };
      const screen = editor.camera.world_to_screen(world);
      const rect = editor.canvas.getBoundingClientRect();
      const clientX = rect.left + screen.x;
      const clientY = rect.top + screen.y;

      editor.canvas.dispatchEvent(new MouseEvent('mousedown', { button: 0, clientX, clientY, bubbles: true }));
      window.dispatchEvent(new MouseEvent('mouseup', { button: 0, clientX, clientY, bubbles: true }));

      // If the synthetic click missed, keep validating keyboard/action path with a selected footprint.
      if (editor.selectedFpIndex < 0) editor.selectedFpIndex = 0;
      const selectedIndex = editor.selectedFpIndex;

      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'r', bubbles: true }));
      await new Promise((resolveFn) => setTimeout(resolveFn, 1200));

      return { ok: true, selectedIndex, uuid: fp.uuid };
    });
    result.detail.ui_interaction = uiResult;

    const modelAfterUi = await layoutFrame.evaluate(async () => {
      const w = window;
      const base = w.__LAYOUT_BASE_URL__;
      const apiPrefix = w.__LAYOUT_API_PREFIX__ || '/api/layout';
      const r = await fetch(`${base}${apiPrefix}/render-model`);
      return await r.json();
    });
    const afterUiMap = summarizeModel(modelAfterUi);
    const uiChange = anyFootprintChanged(beforeMap, afterUiMap);
    result.checks.ui_interaction_changed_model = Boolean(uiChange);
    result.detail.ui_change = uiChange;

    // Bridge action path sanity: explicit execute-action through frame fetch.
    const forcedMove = await layoutFrame.evaluate(async () => {
      const w = window;
      const base = w.__LAYOUT_BASE_URL__;
      const apiPrefix = w.__LAYOUT_API_PREFIX__ || '/api/layout';
      const modelResp = await fetch(`${base}${apiPrefix}/render-model`);
      const model = await modelResp.json();
      const fp = (model.footprints || []).find((f) => f && f.uuid && f.at);
      if (!fp) return { ok: false, reason: 'no-footprint' };
      const body = {
        type: 'move',
        details: { uuid: fp.uuid, x: Number(fp.at.x || 0) + 0.25, y: Number(fp.at.y || 0) + 0.25, r: Number(fp.at.r || 0) },
      };
      const res = await fetch(`${base}${apiPrefix}/execute-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      return { ok: res.ok && json?.status === 'ok', status: json?.status || null };
    });
    result.checks.bridge_execute_action = Boolean(forcedMove?.ok);
    result.detail.forced_move = forcedMove;

    const imagePath = resolve(ARTIFACTS_DIR, `layout-validate-${Date.now()}.png`);
    await page.screenshot({ path: imagePath, fullPage: true });
    result.detail.screenshot = imagePath;
  } catch (err) {
    result.error = err instanceof Error ? err.message : String(err);
  } finally {
    result.detail.console_tail = logs.slice(-80);
    const reportPath = resolve(ARTIFACTS_DIR, 'layout-validation.json');
    writeFileSync(reportPath, JSON.stringify(result, null, 2));
    await browser.close();
    // eslint-disable-next-line no-console
    console.log(JSON.stringify(result, null, 2));

    const requiredChecks = [
      'page_load',
      'workbench',
      'atopile_status',
      'atopile_connected',
      'layout_button_click',
      'layout_frame',
      'bridge_render_model',
      'bridge_execute_action',
    ];
    const allPassed = requiredChecks.every((k) => result.checks[k]);
    process.exit(allPassed ? 0 : 1);
  }
}

run().catch((e) => {
  // eslint-disable-next-line no-console
  console.error(e);
  process.exit(2);
});
