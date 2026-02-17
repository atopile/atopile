# Web IDE End-to-End Testing

This document captures the testing workflow used to validate the web-ide stack reliably before commit.

## What We Learned

- Browser DevTools alone are not enough for this system.
- In OpenVSCode Server, webview traffic is tunneled through VS Code internals, so missing/failing webviews often do not show obvious browser network errors.
- The most reliable signal is a combination of:
  - status bar state (`ato: Connecting...` -> `ato: 8501`)
  - extension logs (`atopile.log`)
  - automated browser checks (Puppeteer)

## Test Strategy

Use layered checks in this order:

1. Stack availability and HTTPS reachability
2. Workbench + extension startup
3. Sidebar/webview functional behavior
4. Layout interaction behavior
5. WS/back-end recovery behavior under failure

## 1) Bring Up Stack

```bash
cd web-ide
./scripts/web-idectl.sh start
./scripts/web-idectl.sh status
```

Expected:
- container is `Up`
- HTTPS URL is shown (typically `https://<host>:3443`)

## 2) Core E2E Smoke Test

Run the general web-ide validator:

```bash
cd web-ide
node scripts/validate.mjs 'https://127.0.0.1:3443/?folder=/home/openvscode-server/workspace' --timeout=90000
```

Expected:
- all checks pass
- status reaches `ato: 8501`
- artifacts are written to `web-ide/artifacts/`

## 3) Layout E2E Test

Run layout-specific validator:

```bash
cd web-ide
node scripts/validate-layout.mjs 'https://127.0.0.1:3443/?folder=/home/openvscode-server/workspace'
```

Expected:
- layout button opens the layout panel
- `render-model` fetch works through the webview bridge
- action endpoint works (`execute-action`)
- report written to `web-ide/artifacts/layout-validation.json`

## 4) WS Recovery Drill (Must Pass)

Keep a browser session open (or run the smoke validator), then force-kill backend:

```bash
podman exec atopile-web-ide sh -lc 'pids=$(pgrep -f "[a]to serve backend" || true); for p in $pids; do kill -9 $p; done'
```

Expected behavior:
- status transitions to reconnecting (`ato: Connecting...` or `ato: Starting...`)
- backend restarts automatically
- status returns to `ato: 8501`
- WS reconnects without getting stuck

## 5) Log Verification

Check extension logs inside the container:

```bash
podman exec atopile-web-ide sh -lc 'for f in /home/openvscode-server/.openvscode-server/data/logs/*/exthost*/atopile.atopile/atopile.log; do echo "== $f =="; tail -n 160 "$f"; done'
```

For WS recovery specifically:

```bash
podman exec atopile-web-ide sh -lc 'for f in /home/openvscode-server/.openvscode-server/data/logs/*/exthost*/atopile.atopile/atopile.log; do echo "== $f =="; grep -n "WsProxy\\|BackendServer: setConnected\\|Recovery attempt\\|ECONNREFUSED\\|backend ready" "$f" | tail -n 120; done'
```

Expected during restart:
- transient retry info lines are acceptable
- final reconnect to `Connected`
- no stuck reconnect loop

## Pre-Commit Acceptance Checklist

- `./scripts/web-idectl.sh start` works on clean restart
- `node scripts/validate.mjs ...` passes
- `node scripts/validate-layout.mjs ...` passes
- WS recovery drill passes
- logs confirm reconnect success
- only intended files are staged

## Practical Rule

Do not declare a webview/network fix complete until it has passed both:
- automated Puppeteer validation
- forced backend restart recovery validation

