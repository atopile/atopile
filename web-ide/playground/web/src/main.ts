import type { ErrorResponse } from "./generated/api-types";

const errorEl = document.getElementById("error") as HTMLDivElement | null;
const retryBtn = document.getElementById("retry") as HTMLButtonElement | null;
const retryLabelEl = document.getElementById("retry-label") as HTMLSpanElement | null;
const terminalEl = document.getElementById("terminal") as HTMLDivElement | null;
const termBodyEl = document.getElementById("term-body") as HTMLDivElement | null;
const canvasEl = document.getElementById("bg-canvas") as HTMLCanvasElement | null;
const menuToggleEl = document.getElementById("menu-toggle") as HTMLButtonElement | null;
const navRightEl = document.getElementById("nav-right") as HTMLDivElement | null;
const footerYearEl = document.getElementById("footer-year") as HTMLSpanElement | null;

let spawning = false;
let msgIdx = 0;
let msgTimer: number | undefined;
let activeLine: HTMLDivElement | null = null;

const MESSAGES: string[] = [
  "Provisioning cloud machine...",
  "Pulling atopile runtime...",
  "Mounting workspace volume...",
  "Starting language server...",
  "Launching IDE...",
];

function completeLine(line: HTMLDivElement | null): void {
  if (!line) return;
  line.classList.remove("active");
  line.classList.add("completed");
  const status = line.querySelector<HTMLSpanElement>(".term-status");
  if (!status) return;
  status.classList.remove("spinner");
  status.classList.add("done");
  status.textContent = "\u2713";
}

function addLine(text: string): void {
  if (!termBodyEl) return;
  completeLine(activeLine);
  const line = document.createElement("div");
  line.className = "term-line active";

  const status = document.createElement("span");
  status.className = "term-status spinner";

  const msg = document.createElement("span");
  msg.className = "term-text";
  msg.textContent = ` ${text}`;

  line.appendChild(status);
  line.appendChild(msg);
  termBodyEl.appendChild(line);
  termBodyEl.scrollTop = termBodyEl.scrollHeight;
  activeLine = line;
}

function tickMessages(): void {
  if (msgIdx >= MESSAGES.length) return;
  addLine(MESSAGES[msgIdx]);
  msgIdx += 1;
  msgTimer = window.setTimeout(tickMessages, 900);
}

async function spawn(): Promise<void> {
  if (spawning) return;
  spawning = true;
  msgIdx = 0;

  if (errorEl) errorEl.textContent = "";
  if (retryBtn) {
    retryBtn.disabled = true;
    retryBtn.classList.add("hidden");
  }
  if (retryLabelEl) retryLabelEl.textContent = "Retry launch";
  if (terminalEl) terminalEl.classList.add("visible");
  if (termBodyEl) termBodyEl.textContent = "";
  activeLine = null;
  tickMessages();

  try {
    const response = await fetch("/api/spawn", { method: "POST" });
    if (response.redirected) {
      if (msgTimer !== undefined) window.clearTimeout(msgTimer);
      addLine("Ready — redirecting...");
      window.location.href = response.url;
      return;
    }

    if (!response.ok) {
      let message = "Spawn failed";
      try {
        const body = (await response.json()) as ErrorResponse;
        if (body.error) message = body.error;
      } catch {
        // Keep default message when error body is not JSON.
      }
      throw new Error(message);
    }

    window.location.reload();
  } catch (error) {
    if (msgTimer !== undefined) window.clearTimeout(msgTimer);
    if (errorEl) {
      errorEl.textContent = error instanceof Error ? error.message : "Unexpected error";
    }
    if (retryBtn) {
      retryBtn.disabled = false;
      retryBtn.classList.remove("hidden");
    }
    if (retryLabelEl) retryLabelEl.textContent = "Retry launch";
    if (terminalEl) terminalEl.classList.remove("visible");
    msgIdx = 0;
  } finally {
    spawning = false;
  }
}

if (retryBtn) {
  retryBtn.addEventListener("click", () => {
    void spawn();
  });
}

function initNavMenu(): void {
  if (!menuToggleEl || !navRightEl) return;
  const closeMenu = (): void => {
    navRightEl.classList.remove("open");
    menuToggleEl.classList.remove("open");
    menuToggleEl.setAttribute("aria-expanded", "false");
  };
  menuToggleEl.addEventListener("click", () => {
    const isOpen = navRightEl.classList.toggle("open");
    menuToggleEl.classList.toggle("open", isOpen);
    menuToggleEl.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });
  navRightEl.querySelectorAll<HTMLAnchorElement>("a").forEach((anchor) => {
    anchor.addEventListener("click", () => {
      closeMenu();
    });
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth > 700) {
      closeMenu();
    }
  });
}

type Point = [number, number];

type Snake = {
  gx: number;
  gy: number;
  dir: number;
  pts: Point[];
  len: number;
  speed: number;
  alpha: number;
  t: number;
  runway: number;
};

function initBackgroundAnimation(): void {
  if (!canvasEl) return;
  const ctx = canvasEl.getContext("2d");
  if (!ctx) return;

  const grid = 48;
  const snakeCount = 7;
  const dx = [1, 0, -1, 0];
  const dy = [0, 1, 0, -1];
  const snakes: Snake[] = [];

  const cols = (): number => Math.ceil(canvasEl.width / grid) + 2;
  const rows = (): number => Math.ceil(canvasEl.height / grid) + 2;
  const resize = (): void => {
    canvasEl.width = window.innerWidth;
    canvasEl.height = window.innerHeight;
  };

  const pickDir = (gx: number, gy: number, exclude: number): number[] => {
    const out: number[] = [];
    const nc = cols();
    const nr = rows();
    for (let dir = 0; dir < 4; dir += 1) {
      if (dir === exclude) continue;
      const tx = gx + dx[dir];
      const ty = gy + dy[dir];
      if (tx >= 0 && tx < nc && ty >= 0 && ty < nr) out.push(dir);
    }
    return out;
  };

  const makeSnake = (): Snake => {
    const gx = Math.floor(Math.random() * cols());
    const gy = Math.floor(Math.random() * rows());
    const dirs = pickDir(gx, gy, -1);
    const dir = dirs[Math.floor(Math.random() * dirs.length)];
    return {
      gx,
      gy,
      dir,
      pts: [[gx * grid, gy * grid]],
      len: 12 + Math.floor(Math.random() * 8),
      speed: 0.45 + Math.random() * 0.5,
      alpha: 0.3 + Math.random() * 0.2,
      t: 0,
      runway: 4 + Math.floor(Math.random() * 8),
    };
  };

  const stepSnake = (snake: Snake): boolean => {
    snake.gx += dx[snake.dir];
    snake.gy += dy[snake.dir];

    const nc = cols();
    const nr = rows();
    if (snake.gx < 0 || snake.gx >= nc || snake.gy < 0 || snake.gy >= nr) {
      return false;
    }

    snake.pts.push([snake.gx * grid, snake.gy * grid]);
    if (snake.pts.length > snake.len + 1) snake.pts.shift();

    snake.runway -= 1;
    const reverse = (snake.dir + 2) % 4;
    const cw = (snake.dir + 1) % 4;
    const ccw = (snake.dir + 3) % 4;
    const fwdX = snake.gx + dx[snake.dir];
    const fwdY = snake.gy + dy[snake.dir];
    const fwdOk = fwdX >= 0 && fwdX < nc && fwdY >= 0 && fwdY < nr;
    const hitWall = !fwdOk;

    if (hitWall || (snake.runway <= 0 && Math.random() < 0.5)) {
      const opts: number[] = [];
      [cw, ccw].forEach((dir) => {
        const tx = snake.gx + dx[dir];
        const ty = snake.gy + dy[dir];
        if (tx >= 0 && tx < nc && ty >= 0 && ty < nr) opts.push(dir);
      });
      if (!hitWall && fwdOk) opts.push(snake.dir);

      if (!opts.length) {
        opts.push(...pickDir(snake.gx, snake.gy, reverse));
      }
      if (!opts.length) return false;

      snake.dir = opts[Math.floor(Math.random() * opts.length)];
      snake.runway = 4 + Math.floor(Math.random() * 9);
    }
    return true;
  };

  const updateSnake = (snake: Snake, dt: number): Snake => {
    snake.t += snake.speed * dt;
    while (snake.t >= 1) {
      snake.t -= 1;
      if (!stepSnake(snake)) return makeSnake();
    }
    return snake;
  };

  const drawSnake = (snake: Snake): void => {
    if (!snake.pts.length) return;
    const last = snake.pts[snake.pts.length - 1];
    const hx = last[0] + dx[snake.dir] * snake.t * grid;
    const hy = last[1] + dy[snake.dir] * snake.t * grid;

    const points: Point[] = snake.pts.slice();
    points.push([hx, hy]);

    ctx.lineWidth = 1.5;
    ctx.lineCap = "square";
    for (let i = 1; i < points.length; i += 1) {
      const alpha = Math.pow(i / (points.length - 1), 1.8) * snake.alpha;
      ctx.strokeStyle = `rgba(249,80,21,${alpha.toFixed(3)})`;
      ctx.beginPath();
      ctx.moveTo(points[i - 1][0], points[i - 1][1]);
      ctx.lineTo(points[i][0], points[i][1]);
      ctx.stroke();
    }
    ctx.fillStyle = `rgba(249,80,21,${Math.min(snake.alpha * 1.8, 0.8).toFixed(3)})`;
    ctx.beginPath();
    ctx.arc(hx, hy, 2, 0, Math.PI * 2);
    ctx.fill();
  };

  resize();
  window.addEventListener("resize", resize);
  for (let i = 0; i < snakeCount; i += 1) {
    const snake = makeSnake();
    const warmup = 20 + Math.floor(Math.random() * 40);
    for (let j = 0; j < warmup; j += 1) {
      stepSnake(snake);
    }
    snakes.push(snake);
  }

  let last = 0;
  const frame = (timestamp: number): void => {
    window.requestAnimationFrame(frame);
    const dt = Math.min((timestamp - last) / 1000, 0.05);
    last = timestamp;
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    for (let i = 0; i < snakes.length; i += 1) {
      snakes[i] = updateSnake(snakes[i], dt);
      drawSnake(snakes[i]);
    }
  };
  window.requestAnimationFrame(frame);
}

window.addEventListener("DOMContentLoaded", () => {
  if (footerYearEl) footerYearEl.textContent = String(new Date().getFullYear());
  initNavMenu();
  initBackgroundAnimation();

  const params = new URLSearchParams(window.location.search);
  const noLaunch = params.get("nolaunch") === "1";
  if (noLaunch) {
    if (retryBtn) {
      retryBtn.disabled = false;
      retryBtn.classList.remove("hidden");
    }
    if (retryLabelEl) retryLabelEl.textContent = "Launch workspace";
    return;
  }
  window.setTimeout(() => {
    void spawn();
  }, 50);
});
