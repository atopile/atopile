import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import fs from 'fs';
import path from 'path';
import type { IncomingMessage, ServerResponse } from 'http';

const SCREENSHOT_DIR =
  process.env.ATOPILE_SCREENSHOT_DIR || '/tmp/atopile-ui-screenshots';
const SCREENSHOT_ROUTE = '/__screenshots';

type ScreenshotOptions = {
  clickAgent?: boolean;
  agentName?: string;
  scrollTop?: boolean;
  scrollDown?: boolean;
  waitMs?: number;
};

function sanitizeName(value: string): string {
  const cleaned = value.replace(/[^a-zA-Z0-9-_]+/g, '-').replace(/^-+|-+$/g, '');
  return cleaned || 'screenshot';
}

async function readJsonBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk.toString();
    });
    req.on('end', () => {
      if (!body.trim()) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

async function takeScreenshot(
  url: string,
  name: string,
  options: ScreenshotOptions = {}
): Promise<string> {
  const puppeteerModule = await import('puppeteer');
  const puppeteer = puppeteerModule.default ?? puppeteerModule;

  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1400, height: 900 });
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

    await new Promise((resolvePromise) =>
      setTimeout(resolvePromise, options.waitMs ?? 1000)
    );

    if (options.clickAgent) {
      try {
        await page.waitForSelector('.card', { timeout: 5000 });
        const agentCards = await page.$$('.card.cursor-pointer');
        if (agentCards.length > 0) {
          let cardToClick = agentCards[agentCards.length - 1];
          if (options.agentName) {
            for (const card of agentCards) {
              const text = await card.evaluate((el) => el.textContent ?? '');
              if (text.includes(options.agentName)) {
                cardToClick = card;
                break;
              }
            }
          }
          await cardToClick.click();
          await new Promise((resolvePromise) => setTimeout(resolvePromise, 2000));
        }
      } catch {
        // Best-effort: no agent card available.
      }
    }

    if (options.scrollTop) {
      await page.evaluate(() => {
        const scrollable = document.querySelector('.output-stream');
        if (scrollable) {
          scrollable.scrollTop = 0;
        }
      });
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 500));
    } else if (options.scrollDown) {
      await page.evaluate(() => {
        const scrollable = document.querySelector('.output-stream');
        if (scrollable) {
          scrollable.scrollTop = scrollable.scrollHeight;
        }
      });
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 500));
    }

    const filename = `${sanitizeName(name)}-${Date.now()}.png`;
    const screenshotPath = path.join(SCREENSHOT_DIR, filename);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    return screenshotPath;
  } finally {
    await browser.close();
  }
}

function screenshotPlugin() {
  return {
    name: 'atopile-screenshot-api',
    configureServer(server: { middlewares: { use: Function } }) {
      server.middlewares.use(
        async (req: IncomingMessage, res: ServerResponse, next: Function) => {
          if (!req.url) {
            next();
            return;
          }

          const base = `http://${req.headers.host || '127.0.0.1:5173'}`;
          const url = new URL(req.url, base);

          if (req.method === 'GET' && url.pathname.startsWith(`${SCREENSHOT_ROUTE}/`)) {
            const filename = path.basename(url.pathname);
            const filePath = path.join(SCREENSHOT_DIR, filename);
            if (!fs.existsSync(filePath)) {
              res.statusCode = 404;
              res.end('Not found');
              return;
            }
            res.setHeader('Content-Type', 'image/png');
            fs.createReadStream(filePath).pipe(res);
            return;
          }

          if (req.method !== 'POST' || url.pathname !== '/api/screenshot') {
            next();
            return;
          }

          try {
            const body = await readJsonBody(req);
            const targetUrl =
              typeof body.url === 'string'
                ? body.url
                : `${base}${typeof body.path === 'string' ? body.path : '/'}`;
            const name = typeof body.name === 'string' ? body.name : 'ui';
            const screenshotPath = await takeScreenshot(targetUrl, name, {
              clickAgent: Boolean(body.clickAgent),
              agentName: typeof body.agentName === 'string' ? body.agentName : undefined,
              scrollTop: Boolean(body.scrollTop),
              scrollDown: Boolean(body.scrollDown),
              waitMs: typeof body.waitMs === 'number' ? body.waitMs : undefined,
            });

            const filename = path.basename(screenshotPath);
            res.setHeader('Content-Type', 'application/json');
            res.end(
              JSON.stringify({
                ok: true,
                url: `${SCREENSHOT_ROUTE}/${filename}`,
                path: screenshotPath,
              })
            );
          } catch (err) {
            res.statusCode = 500;
            res.setHeader('Content-Type', 'application/json');
            res.end(
              JSON.stringify({
                ok: false,
                error: err instanceof Error ? err.message : 'Failed to capture screenshot',
              })
            );
          }
        }
      );
    },
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [react(), screenshotPlugin()],
  // Dev server settings
  server: {
    port: 5173,
    open: true,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      // In production, build the separate webview entry points
      input: mode === 'development' 
        ? resolve(__dirname, 'index.html')
        : {
            sidebar: resolve(__dirname, 'sidebar.html'),
            logViewer: resolve(__dirname, 'log-viewer.html'),
          },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: '[name]-[hash].js',
        assetFileNames: '[name].[ext]',
      },
    },
  },
}));
