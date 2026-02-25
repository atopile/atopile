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

/* ---- Limit expression parsing ---- */

const SI_MULTIPLIERS: Record<string, number> = {
  'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6,
  'm': 1e-3, '': 1, 'k': 1e3, 'M': 1e6, 'G': 1e9,
};

/**
 * Parse a numeric value with optional SI prefix and unit.
 * Examples: "12.5V" → 12.5, "150mV" → 0.15, "4ms" → 0.004, "5%" → 5
 */
function parseValueWithUnit(s: string): number | null {
  s = s.trim();
  // Match: optional sign, number, optional SI prefix, optional unit letters
  const m = s.match(/^([+-]?\d+\.?\d*(?:e[+-]?\d+)?)\s*([fpnumkMG]?)([A-Za-z%]*)?$/);
  if (!m) return null;
  const num = parseFloat(m[1]);
  const prefix = m[2] || '';
  const mult = SI_MULTIPLIERS[prefix];
  if (mult === undefined) return null;
  return num * mult;
}

/**
 * Parse a limit expression into min/max values.
 *
 * Supported formats:
 *   "0s to 4ms"        → { min: 0, max: 0.004 }
 *   "11.5V to 12.5V"   → { min: 11.5, max: 12.5 }
 *   "5V +/- 10%"       → { min: 4.5, max: 5.5 }
 *   "5V +/- 0.5V"      → { min: 4.5, max: 5.5 }
 *   "0 +/- 100mV"      → { min: -0.1, max: 0.1 }
 *
 * Returns null if the expression cannot be parsed.
 */
export function parseLimitExpr(expr: string): { min: number; max: number } | null {
  expr = expr.trim();

  // Pattern 1: "X to Y" range
  const rangeMatch = expr.match(/^(.+?)\s+to\s+(.+)$/i);
  if (rangeMatch) {
    const lo = parseValueWithUnit(rangeMatch[1]);
    const hi = parseValueWithUnit(rangeMatch[2]);
    if (lo !== null && hi !== null) return { min: lo, max: hi };
    return null;
  }

  // Pattern 2: "X +/- Y%" or "X +/- Y<unit>"
  const tolMatch = expr.match(/^(.+?)\s*\+\/-\s*(.+)$/);
  if (tolMatch) {
    const center = parseValueWithUnit(tolMatch[1]);
    if (center === null) return null;
    const tolStr = tolMatch[2].trim();
    if (tolStr.endsWith('%')) {
      const pct = parseFloat(tolStr);
      if (isNaN(pct)) return null;
      const delta = Math.abs(center * pct / 100);
      return { min: center - delta, max: center + delta };
    }
    const delta = parseValueWithUnit(tolStr);
    if (delta === null) return null;
    return { min: center - Math.abs(delta), max: center + Math.abs(delta) };
  }

  return null;
}

/**
 * Re-evaluate pass/fail for a requirement given new min/max limits.
 * Updates `passed` on the requirement and on each sweep point.
 * Returns a partial RequirementData with the changed fields.
 */
export function reEvalPassFail(
  actual: number | null,
  minVal: number,
  maxVal: number,
  sweepPoints?: { paramValue: number; actual: number; passed: boolean }[],
): { passed: boolean; sweepPoints?: { paramValue: number; actual: number; passed: boolean }[] } {
  const updatedSweep = sweepPoints?.map(sp => ({
    ...sp,
    passed: isFinite(sp.actual) && sp.actual >= minVal && sp.actual <= maxVal,
  }));

  let passed: boolean;
  if (updatedSweep && updatedSweep.length > 0) {
    // Sweep: all points must pass
    passed = updatedSweep.every(sp => sp.passed);
  } else if (actual !== null && isFinite(actual)) {
    passed = actual >= minVal && actual <= maxVal;
  } else {
    passed = false;
  }

  return { passed, sweepPoints: updatedSweep };
}
