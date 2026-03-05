import { createServer } from "node:http";
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { PNG } from "pngjs";
import puppeteer, { type Browser } from "puppeteer";

function parseArgs() {
    const args = process.argv.slice(2);
    let dir: string | null = null;
    for (let index = 0; index < args.length; index += 1) {
        if (args[index] === "--dir") {
            dir = args[index + 1] ?? null;
            index += 1;
        }
    }
    if (!dir) {
        throw new Error("Usage: bun run validate --dir <demo-dir>");
    }
    return { dir: path.resolve(dir) };
}

function contentType(filePath: string): string {
    const ext = path.extname(filePath).toLowerCase();
    switch (ext) {
        case ".html":
            return "text/html; charset=utf-8";
        case ".js":
            return "text/javascript; charset=utf-8";
        case ".json":
            return "application/json; charset=utf-8";
        case ".glb":
            return "model/gltf-binary";
        case ".png":
            return "image/png";
        default:
            return "application/octet-stream";
    }
}

async function startStaticServer(rootDir: string) {
    const server = createServer(async (request, response) => {
        try {
            const requestPath = new URL(request.url ?? "/", "http://127.0.0.1").pathname;
            if (requestPath === "/favicon.ico") {
                response.writeHead(204);
                response.end();
                return;
            }
            const relativePath = requestPath === "/" ? "index.html" : requestPath.slice(1);
            const resolvedPath = path.resolve(rootDir, relativePath);
            if (!resolvedPath.startsWith(rootDir)) {
                response.writeHead(403);
                response.end("forbidden");
                return;
            }
            const info = await stat(resolvedPath);
            if (info.isDirectory()) {
                response.writeHead(404);
                response.end("not found");
                return;
            }
            const body = await readFile(resolvedPath);
            response.writeHead(200, { "Content-Type": contentType(resolvedPath) });
            response.end(body);
        } catch {
            response.writeHead(404);
            response.end("not found");
        }
    });

    await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", () => resolve()));
    const address = server.address();
    if (!address || typeof address === "string") {
        throw new Error("Unable to determine validation server address");
    }
    return {
        server,
        baseUrl: `http://127.0.0.1:${address.port}`,
    };
}

function imageSignalRatio(buffer: Buffer): number {
    const png = PNG.sync.read(buffer);
    let active = 0;
    const total = png.width * png.height;
    for (let index = 0; index < png.data.length; index += 4) {
        const r = png.data[index] ?? 0;
        const g = png.data[index + 1] ?? 0;
        const b = png.data[index + 2] ?? 0;
        const a = png.data[index + 3] ?? 0;
        const brightness = (r + g + b) / 3;
        if (a > 0 && brightness > 18) {
            active += 1;
        }
    }
    return total === 0 ? 0 : active / total;
}

async function ensureBrowserInstalled() {
    try {
        const browser = await puppeteer.launch({ headless: true });
        await browser.close();
        return;
    } catch {
        const result = spawnSync("bun", ["x", "puppeteer", "browsers", "install", "chrome"], {
            stdio: "inherit",
        });
        if (result.status !== 0) {
            throw new Error("Unable to install Chrome for Puppeteer");
        }
    }
}

const { dir } = parseArgs();
const screenshotDir = path.resolve(process.env.ATO_DEMO_SCREENSHOT_DIR ?? path.join(dir, "screenshots"));
await mkdir(screenshotDir, { recursive: true });

await ensureBrowserInstalled();
const { server, baseUrl } = await startStaticServer(dir);

const consoleErrors: string[] = [];
let browser: Browser | null = null;

try {
    browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1400, deviceScaleFactor: 1 });

    page.on("console", (message) => {
        if (message.type() === "error" && !message.text().includes("favicon.ico")) {
            consoleErrors.push(message.text());
        }
    });
    page.on("pageerror", (error) => {
        consoleErrors.push(error instanceof Error ? error.message : String(error));
    });

    await page.goto(`${baseUrl}/index.html`, { waitUntil: "load", timeout: 120000 });
    await page.waitForFunction(
        () => window.__ATOPILE_DEMO_READY__ === true || Boolean(window.__ATOPILE_DEMO_STATE__?.error),
        { timeout: 120000 },
    );

    const demoState = await page.evaluate(() => window.__ATOPILE_DEMO_STATE__ ?? null);
    if (demoState?.error) {
        throw new Error(`Demo reported an error: ${demoState.error}`);
    }

    await page.evaluate(() => {
        window.__ATOPILE_DEMO_SET_TOP_DOWN__?.();
    });
    await new Promise((resolve) => setTimeout(resolve, 300));

    const fullPage = path.join(screenshotDir, "demo-full.png");
    await page.screenshot({ path: fullPage, fullPage: true });

    const layoutPane = await page.$("[data-pane='layout']");
    const modelPane = await page.$("[data-pane='model']");
    if (!layoutPane || !modelPane) {
        throw new Error("Could not locate demo panes for screenshot validation");
    }

    const layoutPath = path.join(screenshotDir, "demo-layout.png");
    const modelPath = path.join(screenshotDir, "demo-model.png");
    await layoutPane.screenshot({ path: layoutPath });
    await modelPane.screenshot({ path: modelPath });
    await writeFile(path.join(dir, "poster.png"), await readFile(modelPath));

    const [layoutRatio, modelRatio] = await Promise.all([
        readFile(layoutPath).then(imageSignalRatio),
        readFile(modelPath).then(imageSignalRatio),
    ]);

    if (consoleErrors.length) {
        throw new Error(`Browser console errors during validation:\n${consoleErrors.join("\n")}`);
    }
    if (layoutRatio < 0.005) {
        throw new Error(`Layout screenshot appears empty (signal ratio ${layoutRatio.toFixed(4)})`);
    }
    if (modelRatio < 0.02) {
        throw new Error(`3D screenshot appears empty (signal ratio ${modelRatio.toFixed(4)})`);
    }

    console.log(JSON.stringify({
        ok: true,
        url: `${baseUrl}/index.html`,
        screenshots: {
            full: fullPage,
            layout: layoutPath,
            model: modelPath,
            poster: path.join(dir, "poster.png"),
        },
        signalRatio: {
            layout: layoutRatio,
            model: modelRatio,
        },
    }));
} finally {
    await browser?.close();
    await new Promise<void>((resolve, reject) => {
        server.close((error) => (error ? reject(error) : resolve()));
    });
}
