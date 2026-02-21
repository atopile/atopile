interface MiniTrendCardProps {
  title: string;
  value: string;
  subtitle: string;
  series: number[];
  color: string;
  formatter?: (value: number) => string;
}

function normalize(value: number, min: number, max: number): number {
  if (max <= min) {
    return 0;
  }
  return (value - min) / (max - min);
}

export function MiniTrendCard({
  title,
  value,
  subtitle,
  series,
  color,
  formatter
}: MiniTrendCardProps): JSX.Element {
  const width = 240;
  const height = 92;
  const padding = 8;
  const innerWidth = width - padding * 2;
  const innerHeight = height - padding * 2;

  const values = series.length > 0 ? series : [0, 0];
  const minValue = Math.min(...values, 0);
  const maxValue = Math.max(...values, 1);

  const points = values.map((entry, index) => {
    const x = padding + (index / Math.max(values.length - 1, 1)) * innerWidth;
    const y =
      padding + innerHeight - normalize(entry, minValue, maxValue) * innerHeight;
    return { x, y };
  });

  const linePath = points
    .map((point, index) => {
      return `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.y.toFixed(2)}`;
    })
    .join(" ");

  const fillPath = `${linePath} L${(
    padding + innerWidth
  ).toFixed(2)},${(padding + innerHeight).toFixed(2)} L${padding.toFixed(2)},${(
    padding + innerHeight
  ).toFixed(2)} Z`;

  const latest = points[points.length - 1];
  const latestValue = values[values.length - 1];
  const prevValue = values[Math.max(values.length - 2, 0)];
  const delta = latestValue - prevValue;
  const deltaPct =
    Math.abs(prevValue) > 0.00001 ? (delta / Math.abs(prevValue)) * 100 : null;
  const deltaLabel =
    deltaPct === null
      ? latestValue === 0
        ? "flat"
        : "new"
      : `${deltaPct >= 0 ? "+" : ""}${deltaPct.toFixed(1)}%`;
  const deltaClass =
    delta > 0 ? "positive" : delta < 0 ? "negative" : "neutral";
  const formatPoint = formatter ?? ((point: number) => point.toFixed(1));
  const gradientId = `mini-fill-${title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`;

  return (
    <article className="card mini-trend-card">
      <header>
        <div className="mini-heading-row">
          <p className="mini-title">{title}</p>
          <span className={`mini-delta ${deltaClass}`}>{deltaLabel}</span>
        </div>
        <p className="mini-value">{value}</p>
        <p className="mini-subtitle">{subtitle}</p>
      </header>
      <svg viewBox={`0 0 ${width} ${height}`} className="mini-trend-chart" role="img">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={`${color}44`} />
            <stop offset="100%" stopColor={`${color}00`} />
          </linearGradient>
        </defs>
        <path d={fillPath} fill={`url(#${gradientId})`} />
        <path d={linePath} fill="none" stroke={color} strokeWidth="1.2" />
        <circle cx={latest.x} cy={latest.y} r="2.4" fill={color} />
      </svg>
      <footer className="mini-chart-meta">
        <span>min {formatPoint(minValue)}</span>
        <span>max {formatPoint(maxValue)}</span>
      </footer>
    </article>
  );
}
