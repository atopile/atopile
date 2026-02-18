# Web IDE NetworkError Fix — Summary

## Symptom

During builds in the web IDE, the browser console was flooded with:

```
Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource
at http://localhost:8501/api/builds/active. (Reason: CORS request did not succeed).

[WS] Failed to refresh builds: TypeError: NetworkError when attempting to fetch resource.
```

Every build stage transition produced these errors, resulting in 20+ failures per build.

## Root Cause

The **LogViewerProvider** was missing the HTTP fetch proxy (`__ATOPILE_PROXY_FETCH__`).

Both the sidebar and log viewer webviews run inside cross-origin iframes hosted on
`vscode-cdn.net`. From there, direct `fetch()` calls to `http://localhost:8501` are
blocked by the browser's Same-Origin Policy (CORS / Mixed Content).

The **SidebarProvider** already had two proxies injected into its webview HTML:
- `window.__ATOPILE_PROXY_FETCH__` — routes HTTP requests through `postMessage` →
  extension host → Node.js `fetch` → backend
- `ProxyWebSocket` — routes WebSocket connections through the same bridge

The **LogViewerProvider** only had the WebSocket proxy. It was missing the fetch proxy.

Both webviews load the shared `AppProvider`, which establishes a WebSocket connection
and handles `BuildsChanged` events by calling `refreshBuilds()`. The call chain:

1. WebSocket receives `BuildsChanged` event (via proxy — **works**)
2. `refreshBuilds()` calls `fetchJSON("/api/builds/active")`
3. `getProxyFetch()` checks for `window.__ATOPILE_PROXY_FETCH__` — returns **null**
4. Falls back to native `fetch("http://localhost:8501/api/builds/active")`
5. Browser blocks the cross-origin request → **NetworkError**

## Fix

### `src/vscode-atopile/src/providers/LogViewerProvider.ts`

1. Added `__ATOPILE_PROXY_FETCH__` inline script to the webview HTML (same implementation
   as SidebarProvider) — includes `normalizeHeaders`, the pending-request Map, and the
   `fetchProxyResult` message listener.
2. Added `fetchProxy` message handler (`_handleFetchProxy`) so the extension host forwards
   proxied HTTP requests to the backend via Node.js `fetch`.

### `src/ui-server/src/api/websocket.ts`

Added debounce + mutex wrapper around `refreshBuilds()` (nice-to-have, not the root fix).
Rapid `BuildsChanged` events now collapse into at most one HTTP request per 300ms window,
with a trailing re-fetch if events arrived during an in-flight request.

## Investigation Process

1. Initial hypothesis was request volume overwhelming Firefox's fetch interception →
   added debounce. Deployed, but error persisted.
2. Built Puppeteer investigation scripts to observe behavior during builds. Chromium
   showed 0 errors (fetch proxy worked in sidebar), but couldn't reproduce the
   Firefox-specific CORS errors.
3. Added instrumentation logging to `fetchJSON` and `debouncedRefreshBuilds`. Deployed,
   but **none of the instrumentation appeared** in the user's browser console — and the
   JS bundle hash differed. This revealed the errors came from the **log viewer** webview
   (separate bundle), not the sidebar.
4. Compared `SidebarProvider._getProdHtml()` with `LogViewerProvider._getProdHtml()` →
   found the missing `__ATOPILE_PROXY_FETCH__` setup. Added it. Error resolved.

## Files Changed

| File | Change |
|------|--------|
| `src/vscode-atopile/src/providers/LogViewerProvider.ts` | Added fetch proxy (inline script + message handler) |
| `src/ui-server/src/api/websocket.ts` | Added debounce wrapper for `refreshBuilds()` |
