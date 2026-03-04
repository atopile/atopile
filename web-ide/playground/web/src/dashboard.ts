import type { DashboardPoint, DashboardSeriesResponse } from "./generated/api-types";

const canvasEl = document.getElementById("chart") as HTMLCanvasElement | null;
const errorEl = document.getElementById("error") as HTMLDivElement | null;
const activeValueEl = document.getElementById("active-value") as HTMLDivElement | null;
const warmValueEl = document.getElementById("warm-value") as HTMLDivElement | null;
const totalValueEl = document.getElementById("total-value") as HTMLDivElement | null;
const maxValueEl = document.getElementById("max-value") as HTMLDivElement | null;
const updatedAtEl = document.getElementById("updated-at") as HTMLDivElement | null;
const rangeButtons = Array.from(
  document.querySelectorAll<HTMLButtonElement>(".range-button[data-window]"),
);

let selectedWindowSeconds = 3600;
let pollTimer: number | undefined;

function setError(message: string): void {
  if (errorEl) {
    errorEl.textContent = message;
  }
}

function resizeCanvas(canvas: HTMLCanvasElement): CanvasRenderingContext2D | null {
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const width = Math.max(1, canvas.clientWidth);
  const height = Math.max(1, canvas.clientHeight);
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}

function drawSeries(
  ctx: CanvasRenderingContext2D,
  points: DashboardPoint[],
  valueKey: "active" | "warm" | "total",
  color: string,
  maxY: number,
  chartWidth: number,
  chartHeight: number,
): void {
  const left = 44;
  const right = chartWidth - 14;
  const top = 12;
  const bottom = chartHeight - 26;
  const spanX = Math.max(1, right - left);
  const spanY = Math.max(1, bottom - top);
  const count = points.length;
  if (!count) return;

  ctx.beginPath();
  for (let i = 0; i < count; i += 1) {
    const ratioX = count === 1 ? 1 : i / (count - 1);
    const x = left + ratioX * spanX;
    const ratioY = points[i][valueKey] / maxY;
    const y = bottom - ratioY * spanY;
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.lineWidth = 2;
  ctx.strokeStyle = color;
  ctx.stroke();
}

function drawChart(points: DashboardPoint[]): void {
  if (!canvasEl) return;
  const ctx = resizeCanvas(canvasEl);
  if (!ctx) return;

  const width = canvasEl.clientWidth;
  const height = canvasEl.clientHeight;
  ctx.clearRect(0, 0, width, height);

  if (!points.length) {
    ctx.fillStyle = "#7f8ea1";
    ctx.font = "12px JetBrains Mono";
    ctx.fillText("No datapoints yet.", 16, 24);
    return;
  }

  const maxSeriesValue = Math.max(
    1,
    ...points.map((point) => Math.max(point.active, point.warm, point.total)),
  );
  const axisMax = Math.max(1, Math.ceil(maxSeriesValue * 1.1));

  const left = 44;
  const right = width - 14;
  const top = 12;
  const bottom = height - 26;

  ctx.strokeStyle = "rgba(255,255,255,0.18)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(left, top);
  ctx.lineTo(left, bottom);
  ctx.lineTo(right, bottom);
  ctx.stroke();

  ctx.fillStyle = "#7f8ea1";
  ctx.font = "10px JetBrains Mono";
  ctx.fillText(String(axisMax), 8, top + 3);
  ctx.fillText("0", 24, bottom + 3);

  const startLabel = new Date(points[0].timestamp_ms).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  const endLabel = new Date(points[points.length - 1].timestamp_ms).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  ctx.fillText(startLabel, left, height - 8);
  const endWidth = ctx.measureText(endLabel).width;
  ctx.fillText(endLabel, right - endWidth, height - 8);

  drawSeries(ctx, points, "active", "#f95015", axisMax, width, height);
  drawSeries(ctx, points, "warm", "#f7b731", axisMax, width, height);
  drawSeries(ctx, points, "total", "#2ad6c4", axisMax, width, height);
}

async function refreshDashboard(): Promise<void> {
  try {
    const response = await fetch(`/api/dashboard/series?window_seconds=${selectedWindowSeconds}`);
    if (!response.ok) {
      throw new Error("Failed to load machine history");
    }
    const data = (await response.json()) as DashboardSeriesResponse;

    if (activeValueEl) activeValueEl.textContent = String(data.active);
    if (warmValueEl) warmValueEl.textContent = String(data.warm);
    if (totalValueEl) totalValueEl.textContent = String(data.total);
    if (maxValueEl) {
      maxValueEl.textContent = data.max_machine_count === null ? "unbounded" : String(data.max_machine_count);
    }
    if (updatedAtEl) {
      updatedAtEl.textContent = `updated: ${new Date().toLocaleTimeString()}`;
    }

    drawChart(data.points);
    setError("");
  } catch (error) {
    drawChart([]);
    setError(error instanceof Error ? error.message : "Failed to refresh dashboard");
  }
}

function selectWindow(seconds: number): void {
  selectedWindowSeconds = seconds;
  for (const button of rangeButtons) {
    button.classList.toggle("active", Number(button.dataset.window) === selectedWindowSeconds);
  }
  void refreshDashboard();
}

function startPolling(): void {
  if (pollTimer !== undefined) {
    window.clearInterval(pollTimer);
  }
  pollTimer = window.setInterval(() => {
    void refreshDashboard();
  }, 10000);
}

window.addEventListener("DOMContentLoaded", () => {
  if (!canvasEl) return;

  for (const button of rangeButtons) {
    button.addEventListener("click", () => {
      const value = Number(button.dataset.window);
      if (!Number.isFinite(value) || value <= 0) return;
      selectWindow(value);
    });
  }

  window.addEventListener("resize", () => {
    void refreshDashboard();
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      void refreshDashboard();
    }
  });

  startPolling();
  void refreshDashboard();
});
