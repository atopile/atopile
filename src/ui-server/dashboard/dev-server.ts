/**
 * Thin dev server: proxies WebSocket to Python backend, serves viewer pages.
 * All state lives in Python. Usage: npx tsx dashboard/dev-server.ts
 */
import { WebSocketServer, WebSocket } from 'ws';
import * as http from 'http';

const DEV_WS_PORT = 3001, HTTP_PORT = 3002;
const BACKEND_WS = process.env.VITE_WS_URL
  || process.env.BACKEND_WS
  || (process.env.VITE_API_URL ? `${process.env.VITE_API_URL.replace(/^http/, 'ws')}/ws/state` : '');

if (!BACKEND_WS) {
  throw new Error('BACKEND_WS not configured. Set VITE_WS_URL or VITE_API_URL.');
}

// WebSocket proxy: Browser <-> Dev Server <-> Python Backend
const wss = new WebSocketServer({ port: DEV_WS_PORT });

wss.on('connection', (clientWs: WebSocket) => {
  console.log('[WS] Client connected, proxying to backend');

  // Connect to Python backend
  const backendWs = new WebSocket(BACKEND_WS);
  let isOpen = false;

  backendWs.on('open', () => {
    isOpen = true;
    console.log('[WS] Connected to Python backend');
  });

  backendWs.on('message', (data) => {
    // Forward backend -> client
    if (clientWs.readyState === WebSocket.OPEN) {
      clientWs.send(data.toString());
    }
  });

  backendWs.on('error', (err) => {
    console.error('[WS] Backend error:', err.message);
    clientWs.close(1011, 'Backend connection error');
  });

  backendWs.on('close', () => {
    console.log('[WS] Backend connection closed');
    clientWs.close(1000, 'Backend disconnected');
  });

  clientWs.on('message', (data) => {
    // Forward client -> backend
    if (isOpen && backendWs.readyState === WebSocket.OPEN) {
      backendWs.send(data.toString());
    }
  });

  clientWs.on('close', () => {
    console.log('[WS] Client disconnected');
    backendWs.close();
  });

  clientWs.on('error', (err) => {
    console.error('[WS] Client error:', err.message);
    backendWs.close();
  });
});

// Simple HTTP server for viewer pages
const httpServer = http.createServer((req, res) => {
  const url = new URL(req.url || '/', `http://localhost:${HTTP_PORT}`);

  // Serve viewer HTML pages
  if (url.pathname === '/layout' || url.pathname === '/3d') {
    const html = `<!DOCTYPE html>
<html>
<head><title>Viewer</title></head>
<body>
  <h1>${url.pathname === '/layout' ? 'Layout' : '3D'} Viewer</h1>
  <p>File: ${url.searchParams.get('file') || '(none)'}</p>
  <p>This is a placeholder. Use the Vite dev server for the full UI.</p>
</body>
</html>`;
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
    return;
  }

  res.writeHead(404);
  res.end('Not found');
});

httpServer.listen(HTTP_PORT);

console.log(`Thin Dev Server: WS ws://localhost:${DEV_WS_PORT} -> ${BACKEND_WS}`);
console.log(`Viewer pages: http://localhost:${HTTP_PORT}`);
