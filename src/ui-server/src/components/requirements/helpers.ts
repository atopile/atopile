/** Format a number with engineering prefix (e.g. 7.5 V, 250 uA) */
export function formatEng(value: number, unit: string): string {
  if (unit === '%') return `${value.toFixed(2)}%`;
  const prefixes: [number, string][] = [
    [1e-15, 'f'], [1e-12, 'p'], [1e-9, 'n'], [1e-6, 'u'],
    [1e-3, 'm'], [1, ''], [1e3, 'k'], [1e6, 'M'], [1e9, 'G'],
  ];
  const abs = Math.abs(value);
  if (abs === 0) return `0 ${unit}`;
  for (const [threshold, prefix] of prefixes) {
    if (abs < threshold * 1000) {
      return `${(value / threshold).toPrecision(4)} ${prefix}${unit}`;
    }
  }
  return `${value.toPrecision(4)} ${unit}`;
}

/** Compute margin percentage (distance to nearest limit as % of span) */
export function computeMargin(actual: number, minVal: number, maxVal: number): number {
  const marginLo = Math.abs(actual - minVal);
  const marginHi = Math.abs(maxVal - actual);
  const nearest = Math.min(marginLo, marginHi);
  const span = maxVal - minVal;
  return span > 0 ? (nearest / span * 100) : 0;
}

/** Pick a time-axis scale factor and unit label */
export function autoScaleTime(tMax: number): [number, string] {
  if (tMax < 1e-6) return [1e9, 'ns'];
  if (tMax < 1e-3) return [1e6, 'us'];
  if (tMax < 1) return [1e3, 'ms'];
  return [1, 's'];
}

/** Format an ISO timestamp to a compact local string */
export function formatBuildTime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/** Margin level for color coding */
export function marginLevel(margin: number): 'high' | 'medium' | 'low' {
  if (margin > 40) return 'high';
  if (margin > 15) return 'medium';
  return 'low';
}
