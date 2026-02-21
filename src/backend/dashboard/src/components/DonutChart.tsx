interface DonutSlice {
  label: string;
  value: number;
}

interface DonutChartProps {
  title: string;
  slices: DonutSlice[];
}

const COLORS = [
  "#f95015",
  "#89b4fa",
  "#94e2d5",
  "#f9e2af",
  "#cba6f7",
  "#fab387",
  "#a6e3a1"
];

function polarToCartesian(cx: number, cy: number, radius: number, angle: number) {
  const radians = ((angle - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians)
  };
}

function describeArc(
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number
): string {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return [
    "M",
    start.x,
    start.y,
    "A",
    radius,
    radius,
    0,
    largeArcFlag,
    0,
    end.x,
    end.y
  ].join(" ");
}

export function DonutChart({ title, slices }: DonutChartProps): JSX.Element {
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);

  return (
    <section className="card donut-card" aria-label={title}>
      <h3>{title}</h3>
      {slices.length === 0 || total <= 0 ? (
        <div className="empty-state">No selection traffic yet</div>
      ) : (
        <div className="donut-layout">
          <svg
            viewBox="0 0 220 220"
            className="donut-plot"
            role="img"
            aria-label="Component type demand"
          >
            <circle cx="110" cy="110" r="84" className="donut-ring" />
            {slices.map((slice, index) => {
              const startRatio =
                slices
                  .slice(0, index)
                  .reduce((sum, entry) => sum + entry.value, 0) / total;
              const endRatio = startRatio + slice.value / total;
              const startAngle = startRatio * 360;
              const endAngle = endRatio * 360;
              return (
                <path
                  key={slice.label}
                  d={describeArc(110, 110, 84, startAngle, endAngle)}
                  stroke={COLORS[index % COLORS.length]}
                  strokeWidth="20"
                  fill="none"
                  strokeLinecap="round"
                />
              );
            })}
            <text x="110" y="106" textAnchor="middle" className="donut-total-label">
              total
            </text>
            <text x="110" y="128" textAnchor="middle" className="donut-total-value">
              {total}
            </text>
          </svg>
          <ul className="donut-legend">
            {slices.map((slice, index) => {
              const pct = (slice.value / total) * 100;
              return (
                <li key={slice.label}>
                  <span
                    className="legend-dot"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    aria-hidden="true"
                  />
                  <span className="legend-label">{slice.label}</span>
                  <span className="legend-value">{pct.toFixed(1)}%</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}
