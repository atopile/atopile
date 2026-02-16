import { useState } from "react";

import { formatMs } from "../lib/format";
import type { TimelinePoint } from "../types";

interface CorrelationChartProps {
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

export function CorrelationChart({ points }: CorrelationChartProps): JSX.Element {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const width = 380;
  const height = 292;
  const margin = {
    top: 24,
    right: 16,
    bottom: 40,
    left: 44
  };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  if (points.length === 0) {
    return <div className="empty-state">No data yet</div>;
  }

  const rpmValues = points.map((point) => point.requests_per_min);
  const latencyValues = points.map((point) => point.p95_ms);
  const rpmTicks = buildTicks(Math.max(...rpmValues, 1), 4);
  const latencyTicks = buildTicks(Math.max(...latencyValues, 1), 4);
  const xMax = rpmTicks[rpmTicks.length - 1] ?? 1;
  const yMax = latencyTicks[latencyTicks.length - 1] ?? 1;

  const projected = points.map((point, index) => {
    const x = margin.left + (point.requests_per_min / xMax) * plotWidth;
    const y = margin.top + plotHeight - (point.p95_ms / yMax) * plotHeight;
    return {
      index,
      x,
      y,
      source: point
    };
  });

  const activeIndex = hoverIndex ?? projected.length - 1;
  const activePoint = projected[activeIndex];
  const riskLoadThreshold = xMax * 0.7;
  const riskLatencyThreshold = yMax * 0.7;
  const riskX = margin.left + (riskLoadThreshold / xMax) * plotWidth;
  const riskY = margin.top + plotHeight - (riskLatencyThreshold / yMax) * plotHeight;
  const tooltipX = clamp(activePoint.x + 10, margin.left + 8, margin.left + plotWidth - 150);
  const tooltipY = clamp(activePoint.y - 60, margin.top + 6, margin.top + plotHeight - 50);

  return (
    <div className="scatter-shell">
      <svg viewBox={`0 0 ${width} ${height}`} className="scatter-chart" role="img">
        <rect
          x={riskX}
          y={margin.top}
          width={margin.left + plotWidth - riskX}
          height={riskY - margin.top}
          className="scatter-risk-zone"
        />

        {latencyTicks.map((tick) => {
          const y = margin.top + plotHeight - (tick / yMax) * plotHeight;
          return (
            <g key={`latency-tick-${tick}`}>
              <line x1={margin.left} x2={margin.left + plotWidth} y1={y} y2={y} className="scatter-grid" />
              <text x={margin.left - 8} y={y + 3} textAnchor="end" className="scatter-axis-label">
                {Math.round(tick)}
              </text>
            </g>
          );
        })}

        {rpmTicks.map((tick) => {
          const x = margin.left + (tick / xMax) * plotWidth;
          return (
            <g key={`rpm-tick-${tick}`}>
              <line x1={x} x2={x} y1={margin.top} y2={margin.top + plotHeight} className="scatter-grid vertical" />
              <text x={x} y={height - 18} textAnchor="middle" className="scatter-axis-label">
                {tick.toFixed(tick < 10 ? 1 : 0)}
              </text>
            </g>
          );
        })}

        <line
          x1={margin.left}
          x2={margin.left + plotWidth}
          y1={margin.top + plotHeight}
          y2={margin.top + plotHeight}
          className="scatter-axis"
        />
        <line
          x1={margin.left}
          x2={margin.left}
          y1={margin.top}
          y2={margin.top + plotHeight}
          className="scatter-axis"
        />

        {projected.map((point, index) => {
          const ageRatio = (index + 1) / projected.length;
          const radius = 2.6 + ageRatio * 2.8;
          return (
            <circle
              key={`${point.source.timestamp}-${index}`}
              cx={point.x}
              cy={point.y}
              r={radius}
              className={`scatter-dot ${index === activeIndex ? "active" : ""}`}
              style={{ opacity: 0.2 + ageRatio * 0.72 }}
              onMouseEnter={() => {
                setHoverIndex(index);
              }}
            />
          );
        })}

        <line
          x1={activePoint.x}
          x2={activePoint.x}
          y1={margin.top}
          y2={margin.top + plotHeight}
          className="scatter-hover"
        />
        <line
          x1={margin.left}
          x2={margin.left + plotWidth}
          y1={activePoint.y}
          y2={activePoint.y}
          className="scatter-hover"
        />

        <g transform={`translate(${tooltipX.toFixed(1)} ${tooltipY.toFixed(1)})`}>
          <rect width="148" height="46" rx="9" className="chart-tooltip-bg" />
          <text x="10" y="15" className="chart-tooltip-time">
            {formatAxisTime(activePoint.source.timestamp)}
          </text>
          <text x="10" y="31" className="chart-tooltip-value">
            {activePoint.source.requests_per_min.toFixed(1)} rpm
          </text>
          <text x="10" y="43" className="chart-tooltip-value muted">
            {formatMs(activePoint.source.p95_ms)}
          </text>
        </g>

        <text x={margin.left} y={height - 4} className="scatter-label" textAnchor="start">
          requests / min
        </text>
        <text x={8} y={margin.top - 8} className="scatter-label" textAnchor="start">
          p95 ms
        </text>
        <text x={riskX + 4} y={margin.top + 14} className="scatter-risk-label">
          high load + high latency
        </text>
      </svg>
    </div>
  );
}
