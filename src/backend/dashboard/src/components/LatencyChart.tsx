import { useState } from "react";

import { formatMs } from "../lib/format";
import type { TimelinePoint } from "../types";

interface LatencyChartProps {
  points: TimelinePoint[];
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function niceStep(maxValue: number, targetTicks: number): number {
  const safeMax = Math.max(maxValue, 1);
  const rawStep = safeMax / Math.max(targetTicks, 2);
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const residual = rawStep / magnitude;
  if (residual <= 1) {
    return magnitude;
  }
  if (residual <= 2) {
    return 2 * magnitude;
  }
  if (residual <= 5) {
    return 5 * magnitude;
  }
  return 10 * magnitude;
}

function buildTicks(maxValue: number, targetTicks = 4): number[] {
  const step = niceStep(maxValue, targetTicks);
  const boundedMax = Math.max(step, Math.ceil(maxValue / step) * step);
  const ticks: number[] = [];
  for (let value = 0; value <= boundedMax + step * 0.5; value += step) {
    ticks.push(value);
  }
  return ticks;
}

function formatAxisTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });
}

export function LatencyChart({ points }: LatencyChartProps): JSX.Element {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (points.length === 0) {
    return <div className="empty-state">No traffic yet</div>;
  }

  const width = 860;
  const height = 292;
  const margin = {
    top: 26,
    right: 62,
    bottom: 32,
    left: 56
  };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const rpmValues = points.map((point) => point.requests_per_min);
  const latencyValues = points.map((point) => point.p95_ms);

  const rpmTicks = buildTicks(Math.max(...rpmValues, 1), 4);
  const latencyTicks = buildTicks(Math.max(...latencyValues, 1), 4);

  const rpmMax = rpmTicks[rpmTicks.length - 1] ?? 1;
  const latencyMax = latencyTicks[latencyTicks.length - 1] ?? 1;

  const projected = points.map((point, index) => {
    const x =
      margin.left + (index / Math.max(points.length - 1, 1)) * plotWidth;
    const rpmY = margin.top + plotHeight - (point.requests_per_min / rpmMax) * plotHeight;
    const latencyY = margin.top + plotHeight - (point.p95_ms / latencyMax) * plotHeight;
    return {
      index,
      x,
      rpmY,
      latencyY,
      source: point
    };
  });

  const rpmPath = projected
    .map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.rpmY.toFixed(2)}`)
    .join(" ");
  const latencyPath = projected
    .map((point, index) =>
      `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.latencyY.toFixed(2)}`
    )
    .join(" ");

  const latencyFillPath = `${latencyPath} L${(
    margin.left + plotWidth
  ).toFixed(2)},${(margin.top + plotHeight).toFixed(2)} L${margin.left.toFixed(2)},${(
    margin.top + plotHeight
  ).toFixed(2)} Z`;

  const xTickIndices = Array.from(
    new Set(
      [0, 0.25, 0.5, 0.75, 1]
        .map((ratio) => Math.round(ratio * Math.max(points.length - 1, 0)))
        .filter((value) => value >= 0 && value < points.length)
    )
  );

  const activeIndex = hoverIndex ?? points.length - 1;
  const activePoint = projected[activeIndex];
  const activeTimestamp = formatAxisTime(activePoint.source.timestamp);
  const latencyBudgetMs = 120;
  const budgetY =
    margin.top +
    plotHeight -
    clamp(latencyBudgetMs / latencyMax, 0, 1) * plotHeight;
  const tooltipX = clamp(activePoint.x + 12, margin.left + 8, margin.left + plotWidth - 150);
  const tooltipY = clamp(activePoint.latencyY - 66, margin.top + 8, margin.top + plotHeight - 54);

  return (
    <div className="chart-shell">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="latency-chart"
        role="img"
        aria-label="Traffic and latency timeline"
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          const ratio = clamp((event.clientX - rect.left) / rect.width, 0, 1);
          const nextIndex = Math.round(ratio * Math.max(points.length - 1, 0));
          setHoverIndex(nextIndex);
        }}
        onMouseLeave={() => {
          setHoverIndex(null);
        }}
      >
        <defs>
          <linearGradient id="latencyFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(88, 166, 255, 0.24)" />
            <stop offset="100%" stopColor="rgba(88, 166, 255, 0)" />
          </linearGradient>
        </defs>

        {latencyTicks.map((tick) => {
          const y = margin.top + plotHeight - (tick / latencyMax) * plotHeight;
          return (
            <g key={`latency-grid-${tick}`}>
              <line
                x1={margin.left}
                x2={margin.left + plotWidth}
                y1={y}
                y2={y}
                className="chart-grid-line"
              />
              <text x={margin.left - 8} y={y + 3} textAnchor="end" className="chart-y-axis">
                {Math.round(tick)} ms
              </text>
            </g>
          );
        })}

        {rpmTicks.map((tick) => {
          const y = margin.top + plotHeight - (tick / rpmMax) * plotHeight;
          return (
            <text
              key={`rpm-axis-${tick}`}
              x={margin.left + plotWidth + 8}
              y={y + 3}
              textAnchor="start"
              className="chart-y-axis right"
            >
              {tick.toFixed(tick < 10 ? 1 : 0)} rpm
            </text>
          );
        })}

        <line
          x1={margin.left}
          x2={margin.left + plotWidth}
          y1={budgetY}
          y2={budgetY}
          className="chart-threshold"
        />
        <text x={margin.left + 6} y={budgetY - 6} className="chart-threshold-label">
          latency budget 120 ms
        </text>

        <path d={latencyFillPath} fill="url(#latencyFill)" />
        <path d={rpmPath} fill="none" stroke="#f97316" strokeWidth="1.8" opacity="0.82" />
        <path d={latencyPath} fill="none" stroke="#58a6ff" strokeWidth="2" />

        {xTickIndices.map((index) => {
          const point = projected[index];
          return (
            <text
              key={`x-tick-${index}`}
              x={point.x}
              y={height - 8}
              textAnchor="middle"
              className="chart-x-axis"
            >
              {formatAxisTime(point.source.timestamp)}
            </text>
          );
        })}

        <line
          x1={activePoint.x}
          x2={activePoint.x}
          y1={margin.top}
          y2={margin.top + plotHeight}
          className="chart-hover-line"
        />

        <circle cx={activePoint.x} cy={activePoint.latencyY} r="3.6" className="chart-dot-latency" />
        <circle cx={activePoint.x} cy={activePoint.rpmY} r="3.2" className="chart-dot-rpm" />

        <g transform={`translate(${tooltipX.toFixed(1)} ${tooltipY.toFixed(1)})`}>
          <rect width="148" height="52" rx="9" className="chart-tooltip-bg" />
          <text x="10" y="15" className="chart-tooltip-time">
            {activeTimestamp}
          </text>
          <text x="10" y="31" className="chart-tooltip-value">
            P95 {formatMs(activePoint.source.p95_ms)}
          </text>
          <text x="10" y="45" className="chart-tooltip-value muted">
            {activePoint.source.requests_per_min.toFixed(1)} rpm
          </text>
        </g>
      </svg>
    </div>
  );
}
