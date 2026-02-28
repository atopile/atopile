import type { RequirementData, PlotMeta } from './types';
import { formatEng, autoScaleTime } from './helpers';

type Plotly = typeof import('plotly.js-basic-dist-min');

/** Human-readable measurement labels */
const MEASUREMENT_LABELS: Record<string, string> = {
  final_value: 'Final Value',
  average: 'Average',
  settling_time: 'Settling Time',
  peak_to_peak: 'Peak-to-Peak',
  overshoot: 'Overshoot',
  rms: 'RMS',
  envelope: 'Envelope',
  max: 'Max',
  min: 'Min',
  duty_cycle: 'Duty Cycle',
  frequency: 'Frequency',
  sweep: 'Sweep',
  gain_db: 'Gain (dB)',
  phase_deg: 'Phase (deg)',
  bandwidth_3db: 'Bandwidth 3dB',
  bode_plot: 'Bode Plot',
  efficiency: 'Efficiency',
};

/**
 * Clean up a raw SPICE signal key for display.
 * "v(dut_power_out_hv)" → "dut.power_out.hv"
 * "i(l1)" → "I(L1)"
 * plain keys pass through with underscores → dots
 */
function formatSignalName(key: string): string {
  const iMatch = key.match(/^i\((.+)\)$/i);
  if (iMatch) return `I(${iMatch[1].toUpperCase()})`;
  const vMatch = key.match(/^v\((.+)\)$/i);
  const inner = vMatch ? vMatch[1] : key;
  return inner.replace(/_/g, '.');
}

/**
 * Build a legend label for a trace.
 * Combines the signal name with an optional measurement descriptor.
 * e.g. "power_out.hv — Final Value"
 */
function legendLabel(signalKey: string, measurement?: string): string {
  const sig = formatSignalName(signalKey);
  if (!measurement) return sig;
  const mLabel = MEASUREMENT_LABELS[measurement] || measurement.replace(/_/g, ' ');
  return `${sig} — ${mLabel}`;
}

let _plotly: Plotly | null = null;
let _plotlyPromise: Promise<Plotly> | null = null;

function getPlotly(): Promise<Plotly> {
  if (_plotly) return Promise.resolve(_plotly);
  if (!_plotlyPromise) {
    _plotlyPromise = import('plotly.js-basic-dist-min').then(m => {
      _plotly = m;
      return m;
    });
  }
  return _plotlyPromise;
}

/** Start loading Plotly immediately — call at page init for parallel load */
export function preloadPlotly(): void {
  getPlotly();
}

/** Read current theme colors from CSS variables */
function themeColors() {
  const s = getComputedStyle(document.documentElement);
  const get = (v: string, fb: string) => s.getPropertyValue(v).trim() || fb;
  return {
    text: get('--text-primary', '#cdd6f4'),
    muted: get('--text-muted', '#7f849c'),
    surface: get('--bg-tertiary', '#313244'),
    success: get('--success', '#a6e3a1'),
    error: get('--error', '#f38ba8'),
    info: get('--info', '#31688e'),
    accent: get('--accent', '#f95015'),
  };
}

/** Fixed 16:9 plot dimensions — matches the Python-side 960x540. */
const PLOT_WIDTH = 960;
const PLOT_HEIGHT = 540;

function fixedDimensions(): { width: number; height: number } {
  return { width: PLOT_WIDTH, height: PLOT_HEIGHT };
}

function baseLayout(colors: ReturnType<typeof themeColors>) {
  return {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: '-apple-system, sans-serif', color: colors.text, size: 9 },
    margin: { t: 18, r: 70, b: 24, l: 36 },
    xaxis: {
      gridcolor: `${colors.surface}66`,
      zerolinecolor: `${colors.surface}99`,
      title: { text: '', font: { size: 9, color: colors.muted } },
      tickfont: { size: 8 },
    },
    yaxis: {
      gridcolor: `${colors.surface}66`,
      zerolinecolor: `${colors.surface}99`,
      title: { text: '', font: { size: 9, color: colors.muted } },
      tickfont: { size: 8 },
    },
    legend: { x: 1.02, xanchor: 'left' as const, y: 1, yanchor: 'top' as const, traceorder: 'normal' as const, font: { size: 8, color: colors.muted } },
    modebar: { bgcolor: 'rgba(0,0,0,0)', color: colors.muted, activecolor: colors.accent },
  };
}

export async function renderTransientPlot(el: HTMLDivElement, req: RequirementData, size?: { width: number; height: number }) {
  const Plotly = await getPlotly();
  const colors = themeColors();
  const ts = req.timeSeries!;
  const tMax = ts.time[ts.time.length - 1];
  const [scale, tUnit] = autoScaleTime(tMax);
  const timeScaled = ts.time.map(t => t * scale);

  const netKey = req.net.startsWith('v(') || req.net.startsWith('i(')
    ? req.net : `v(${req.net})`;
  const nutSignal = ts.signals[netKey] || [];

  const traces: Plotly.Data[] = [];

  const nutLabel = legendLabel(
    (req as any).displayNet || netKey,
    req.measurement,
  );
  traces.push({
    x: timeScaled,
    y: nutSignal,
    type: 'scatter',
    mode: 'lines',
    name: nutLabel,
    line: { color: colors.info, width: 2 },
  });

  // Viridis-sampled context colors
  const ctxColors = ['#481a6c', '#287e8e', '#4bc35b', '#d2e21b'];
  (req.contextNets || []).forEach((cn, i) => {
    const ck = cn.startsWith('v(') || cn.startsWith('i(') ? cn : `v(${cn})`;
    if (ts.signals[ck]) {
      traces.push({
        x: timeScaled,
        y: ts.signals[ck],
        type: 'scatter',
        mode: 'lines',
        name: formatSignalName(ck),
        line: { color: ctxColors[i % ctxColors.length], width: 1, dash: 'dot' },
        yaxis: 'y2',
      });
    }
  });

  const dim = size ?? fixedDimensions();
  const layout: Record<string, unknown> = {
    ...baseLayout(colors),
    width: dim.width,
    height: dim.height,
    title: { text: `<b>${req.name}</b>`, font: { size: 10, color: colors.text } },
    xaxis: { ...baseLayout(colors).xaxis, title: { text: `Time (${tUnit})`, font: { size: 9, color: colors.muted } } },
    yaxis: { ...baseLayout(colors).yaxis, title: { text: (() => {
      if (req.unit === '%' ) return '%';
      if (['frequency', 'settling_time'].includes(req.measurement)) {
        return req.net.startsWith('i(') ? 'A' : 'V';
      }
      return req.unit;
    })(), font: { size: 9, color: colors.muted } } },
    shapes: [] as Record<string, unknown>[],
    annotations: [] as Record<string, unknown>[],
  };

  if (req.contextNets && req.contextNets.length > 0) {
    layout.yaxis2 = {
      ...baseLayout(colors).yaxis,
      title: { text: 'Context', font: { size: 9, color: colors.muted } },
      overlaying: 'y',
      side: 'right',
    };
    (layout.margin as Record<string, number>).r = 100;
  }

  const shapes = layout.shapes as Record<string, unknown>[];
  const annotations = layout.annotations as Record<string, unknown>[];

  if (req.measurement === 'final_value' || req.measurement === 'average' || req.measurement === 'rms') {
    shapes.push({
      type: 'rect', xref: 'paper', yref: 'y',
      x0: 0, x1: 1, y0: req.minVal, y1: req.maxVal,
      fillcolor: `${colors.success}14`, line: { width: 0 },
    });
    shapes.push(
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: req.minVal, y1: req.minVal, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: req.maxVal, y1: req.maxVal, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
    );
    shapes.push({
      type: 'line', xref: 'paper', yref: 'y',
      x0: 0, x1: 1, y0: req.actual, y1: req.actual,
      line: { color: req.passed ? colors.success : colors.error, width: 1.5, dash: 'dash' },
    });
    annotations.push(
      { x: 0.02, y: req.minVal, xref: 'paper', yref: 'y', text: `LSL ${formatEng(req.minVal, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'bottom' },
      { x: 0.02, y: req.maxVal, xref: 'paper', yref: 'y', text: `USL ${formatEng(req.maxVal, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'top' },
      { x: 0.98, y: req.actual ?? 0, xref: 'paper', yref: 'y', text: `${formatEng(req.actual ?? NaN, req.unit)}`, showarrow: false, font: { size: 8, color: req.passed ? colors.success : colors.error }, xanchor: 'right', yanchor: 'bottom' },
    );
    const sigMin = nutSignal.length > 0 ? Math.min(...nutSignal) : req.minVal;
    const sigMax = nutSignal.length > 0 ? Math.max(...nutSignal) : req.maxVal;
    const visibleMin = Math.min(req.minVal, sigMin);
    const visibleMax = Math.max(req.maxVal, sigMax);
    const span = visibleMax - visibleMin;
    const pad = span * 0.15;
    (layout.yaxis as Record<string, unknown>).range = [visibleMin - pad, visibleMax + pad];
  }

  if (req.measurement === 'settling_time') {
    const final = nutSignal[nutSignal.length - 1] || 0;
    const tol = req.settlingTolerance || 0.01;
    const band = Math.abs(final * tol);
    shapes.push({
      type: 'rect', xref: 'paper', yref: 'y',
      x0: 0, x1: 1, y0: final - band, y1: final + band,
      fillcolor: `${colors.success}14`, line: { width: 0 },
    });
    shapes.push(
      { type: 'line', xref: 'x', yref: 'paper', x0: req.minVal * scale, x1: req.minVal * scale, y0: 0, y1: 1, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'x', yref: 'paper', x0: req.maxVal * scale, x1: req.maxVal * scale, y0: 0, y1: 1, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
    );
    const actualSettling = req.actual ?? 0;
    shapes.push({
      type: 'line', xref: 'x', yref: 'paper',
      x0: actualSettling * scale, x1: actualSettling * scale, y0: 0, y1: 1,
      line: { color: req.passed ? colors.success : colors.error, width: 2, dash: 'dash' },
    });
    annotations.push({
      x: actualSettling * scale, y: 0.9, xref: 'x', yref: 'paper',
      text: `Settled @ ${formatEng(actualSettling, 's')}`,
      showarrow: false, font: { size: 8, color: req.passed ? colors.success : colors.error },
      textangle: -90, xanchor: 'left', xshift: 6,
    });
    const pad = band * 2;
    (layout.yaxis as Record<string, unknown>).range = [final - band - pad, final + band + pad];
  }

  if (req.measurement === 'peak_to_peak') {
    const peak = Math.max(...nutSignal);
    const trough = Math.min(...nutSignal);
    const center = (peak + trough) / 2;
    // Show actual peak/trough as thin reference lines
    shapes.push(
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: peak, y1: peak, line: { color: colors.muted, width: 0.75 } },
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: trough, y1: trough, line: { color: colors.muted, width: 0.75 } },
    );
    // Show P-P limit envelope centered on signal: ±limit/2
    if (req.maxVal != null && isFinite(req.maxVal)) {
      const halfMax = req.maxVal / 2;
      shapes.push(
        { type: 'rect', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: center - halfMax, y1: center + halfMax, fillcolor: `${colors.success}14`, line: { width: 0 } },
        { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: center + halfMax, y1: center + halfMax, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
        { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: center - halfMax, y1: center - halfMax, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      );
      annotations.push(
        { x: 0.02, y: center + halfMax, xref: 'paper', yref: 'y', text: `USL ±${formatEng(halfMax, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'bottom' },
        { x: 0.02, y: center - halfMax, xref: 'paper', yref: 'y', text: `USL ±${formatEng(halfMax, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'top' },
      );
    }
    annotations.push({
      x: 0.95, y: center, xref: 'paper', yref: 'y',
      text: `P-P: ${formatEng(req.actual ?? NaN, req.unit)}`,
      showarrow: false, font: { size: 8, color: colors.text },
      bgcolor: 'rgba(0,0,0,0.6)', borderpad: 3,
    });
    const halfMax = (req.maxVal != null && isFinite(req.maxVal)) ? req.maxVal / 2 : (peak - trough) / 2;
    const usl = center + halfMax;
    const lsl = center - halfMax;
    const visibleTop = Math.max(peak, usl);
    const visibleBot = Math.min(trough, lsl);
    const limitSpan = usl - lsl;
    const pad = Math.max(limitSpan * 0.1, (visibleTop - visibleBot) * 0.1);
    (layout.yaxis as Record<string, unknown>).range = [Math.min(visibleBot, lsl) - pad, Math.max(visibleTop, usl) + pad];
  }

  if (req.measurement === 'overshoot') {
    const final = nutSignal[nutSignal.length - 1] || 0;
    const peak = Math.max(...nutSignal);
    const peakIdx = nutSignal.indexOf(peak);
    const peakTime = timeScaled[peakIdx];
    shapes.push({
      type: 'line', xref: 'paper', yref: 'y',
      x0: 0, x1: 1, y0: final, y1: final,
      line: { color: colors.muted, width: 1.5, dash: 'dash' },
    });
    const maxOsV = final * (1 + req.maxVal / 100);
    shapes.push({
      type: 'line', xref: 'paper', yref: 'y',
      x0: 0, x1: 1, y0: maxOsV, y1: maxOsV,
      line: { color: colors.muted, width: 1.5, dash: 'dash' },
    });
    annotations.push(
      { x: 0.02, y: final, xref: 'paper', yref: 'y', text: `Final ${formatEng(final, 'V')}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'top' },
      { x: 0.02, y: maxOsV, xref: 'paper', yref: 'y', text: `Max OS ${req.maxVal}%`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'bottom' },
      { x: peakTime, y: peak, xref: 'x', yref: 'y', text: `OS: ${(req.actual ?? 0).toFixed(2)}%`, showarrow: true, ay: -20, arrowcolor: colors.error, arrowwidth: 1.5, font: { size: 8, color: colors.error } },
    );
    const visibleTop = Math.max(peak, maxOsV);
    const span = visibleTop - final;
    const pad = span * 0.15;
    (layout.yaxis as Record<string, unknown>).range = [final - pad, visibleTop + pad];
  }

  Plotly.newPlot(el, traces, layout as Partial<Plotly.Layout>, {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
  });
}

export async function renderDCPlot(el: HTMLDivElement, req: RequirementData, size?: { width: number; height: number }) {
  const Plotly = await getPlotly();
  const colors = themeColors();
  const actual = req.actual ?? 0;
  const visibleMin = Math.min(req.minVal, actual);
  const visibleMax = Math.max(req.maxVal, actual);
  const range = visibleMax - visibleMin;
  const padding = range * 0.3;

  const dcLabel = legendLabel(req.displayNet || req.net, req.measurement);
  const traces: Plotly.Data[] = [{
    type: 'scatter',
    x: [req.actual],
    y: [''],
    mode: 'markers',
    marker: {
      size: 16,
      color: req.passed ? colors.success : colors.error,
      symbol: 'diamond',
      line: { width: 2, color: req.passed ? colors.success : colors.error },
    },
    name: dcLabel,
  }];

  const dim = size ?? fixedDimensions();
  const layout = {
    ...baseLayout(colors),
    width: dim.width,
    height: dim.height,
    title: { text: `<b>${req.name}</b>`, font: { size: 10, color: colors.text } },
    xaxis: {
      ...baseLayout(colors).xaxis,
      title: { text: req.unit, font: { size: 9, color: colors.muted } },
      range: [visibleMin - padding, visibleMax + padding],
    },
    yaxis: { visible: false, fixedrange: true },
    shapes: [
      { type: 'rect', xref: 'x', yref: 'paper', x0: req.minVal, x1: req.maxVal, y0: 0, y1: 1, fillcolor: `${colors.success}1A`, line: { width: 0 } },
      { type: 'line', xref: 'x', yref: 'paper', x0: req.minVal, x1: req.minVal, y0: 0, y1: 1, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'x', yref: 'paper', x0: req.maxVal, x1: req.maxVal, y0: 0, y1: 1, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'x', yref: 'paper', x0: req.typical, x1: req.typical, y0: 0, y1: 1, line: { color: colors.muted, width: 1, dash: 'dash' } },
    ],
    annotations: [
      { x: req.minVal, y: 0.97, xref: 'x', yref: 'paper', text: 'LSL', showarrow: false, font: { size: 7, color: colors.muted }, yanchor: 'top' },
      { x: req.maxVal, y: 0.97, xref: 'x', yref: 'paper', text: 'USL', showarrow: false, font: { size: 7, color: colors.muted }, yanchor: 'top' },
      { x: req.actual ?? 0, y: 0.03, xref: 'x', yref: 'paper', text: formatEng(req.actual ?? NaN, req.unit), showarrow: false, font: { size: 8, color: req.passed ? colors.success : colors.error }, yanchor: 'bottom' },
    ],
  };

  Plotly.newPlot(el, traces, layout as Partial<Plotly.Layout>, {
    responsive: true,
    displaylogo: false,
    staticPlot: true,
  });
}

export async function renderBodePlot(el: HTMLDivElement, req: RequirementData, size?: { width: number; height: number }) {
  const Plotly = await getPlotly();
  const colors = themeColors();
  const fs = req.frequencySeries!;

  const traces: Plotly.Data[] = [];

  // Gain vs frequency
  traces.push({
    x: fs.freq,
    y: fs.gain_db,
    type: 'scatter',
    mode: 'lines',
    name: 'Gain (dB)',
    line: { color: colors.info, width: 2 },
    xaxis: 'x',
    yaxis: 'y',
  });

  // Phase vs frequency
  traces.push({
    x: fs.freq,
    y: fs.phase_deg,
    type: 'scatter',
    mode: 'lines',
    name: 'Phase (deg)',
    line: { color: '#35b779', width: 2 },
    xaxis: 'x',
    yaxis: 'y2',
  });

  // Find -3dB crossing point
  const dcGain = fs.gain_db[0] ?? 0;
  const threshold = dcGain - 3;
  let bwFreq: number | null = null;
  let bwGain: number | null = null;
  for (let i = 0; i < fs.gain_db.length - 1; i++) {
    if (fs.gain_db[i] >= threshold && fs.gain_db[i + 1] < threshold) {
      const logF0 = Math.log10(fs.freq[i]);
      const logF1 = Math.log10(fs.freq[i + 1]);
      const t = (threshold - fs.gain_db[i]) / (fs.gain_db[i + 1] - fs.gain_db[i]);
      bwFreq = 10 ** (logF0 + t * (logF1 - logF0));
      bwGain = fs.gain_db[i] + t * (fs.gain_db[i + 1] - fs.gain_db[i]);
      break;
    }
  }

  if (bwFreq !== null && bwGain !== null) {
    traces.push({
      x: [bwFreq],
      y: [bwGain],
      type: 'scatter',
      mode: 'markers',
      name: `-3 dB @ ${bwFreq.toPrecision(3)} Hz`,
      marker: { size: 8, color: '#000', symbol: 'circle' },
      xaxis: 'x',
      yaxis: 'y',
    });
  }

  const dim = size ?? fixedDimensions();
  const layout: Record<string, unknown> = {
    ...baseLayout(colors),
    width: dim.width,
    height: dim.height,
    title: { text: `<b>${req.name}</b>`, font: { size: 10, color: colors.text } },
    xaxis: {
      ...baseLayout(colors).xaxis,
      type: 'log',
      title: { text: 'Frequency (Hz)', font: { size: 9, color: colors.muted } },
    },
    yaxis: {
      ...baseLayout(colors).yaxis,
      title: { text: 'Gain (dB)', font: { size: 9, color: colors.info } },
    },
    yaxis2: {
      ...baseLayout(colors).yaxis,
      title: { text: 'Phase (deg)', font: { size: 9, color: '#5ec962' } },
      overlaying: 'y',
      side: 'right',
    },
    shapes: [] as Record<string, unknown>[],
    annotations: [] as Record<string, unknown>[],
  };
  (layout.margin as Record<string, number>).r = 100;

  const shapes = layout.shapes as Record<string, unknown>[];
  const annotations = layout.annotations as Record<string, unknown>[];

  // -3dB threshold line
  shapes.push({
    type: 'line', xref: 'paper', yref: 'y',
    x0: 0, x1: 1, y0: threshold, y1: threshold,
    line: { color: colors.muted, width: 1, dash: 'dot' },
  });

  if (bwFreq !== null && bwGain !== null) {
    annotations.push({
      x: bwFreq, y: bwGain, xref: 'x', yref: 'y',
      text: `-3 dB | ${bwFreq.toPrecision(3)} Hz`,
      showarrow: false,
      xanchor: 'left' as const, yanchor: 'top' as const,
      xshift: 6, yshift: -3,
      font: { size: 7, color: '#000' },
    });
  }

  Plotly.newPlot(el, traces, layout as Partial<Plotly.Layout>, {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
  });
}

export async function renderSweepPlot(el: HTMLDivElement, req: RequirementData, size?: { width: number; height: number }) {
  const Plotly = await getPlotly();
  const colors = themeColors();
  const pts = req.sweepPoints!;
  const xVals = pts.map(p => p.paramValue);
  const yVals = pts.map(p => p.actual);
  const ptColors = pts.map(p => p.passed ? colors.success : colors.error);

  const dim = size ?? fixedDimensions();
  const layout: Record<string, unknown> = {
    ...baseLayout(colors),
    width: dim.width,
    height: dim.height,
    title: { text: `<b>${req.name}</b>`, font: { size: 10, color: colors.text } },
    xaxis: { ...baseLayout(colors).xaxis, title: { text: req.sweepParamName || 'Parameter', font: { size: 9, color: colors.muted } } },
    yaxis: { ...baseLayout(colors).yaxis, title: { text: req.unit, font: { size: 9, color: colors.muted } } },
    shapes: [
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: req.minVal, y1: req.minVal, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: req.maxVal, y1: req.maxVal, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
    ],
  };

  const sweepLabel = legendLabel(req.displayNet || req.net, req.measurement);
  Plotly.newPlot(el, [{
    x: xVals, y: yVals, type: 'scatter', mode: 'lines+markers',
    marker: { size: 8, color: ptColors },
    line: { color: colors.info, width: 2 },
    name: sweepLabel,
  }], layout as Partial<Plotly.Layout>, { responsive: true, displaylogo: false, displayModeBar: false });
}

/**
 * Render a single pre-built Plotly spec at an explicit size.
 * Used by RequirementsAllPage to render individual specs from Python.
 */
export async function renderSpecAtSize(
  el: HTMLDivElement,
  spec: { data: Record<string, unknown>[]; layout: Record<string, unknown> },
  width: number,
  height: number,
) {
  const Plotly = await getPlotly();
  const colors = themeColors();

  // Deep-clone layout so we can mutate without affecting the original
  const layout: Record<string, unknown> = JSON.parse(JSON.stringify(spec.layout));

  layout.paper_bgcolor = 'rgba(0,0,0,0)';
  layout.plot_bgcolor = 'rgba(0,0,0,0)';
  layout.width = width;
  layout.height = height;

  const font = (layout.font ?? {}) as Record<string, unknown>;
  font.color = colors.text;
  font.family = '-apple-system, sans-serif';
  font.size = 9;
  layout.font = font;

  layout.modebar = { bgcolor: 'rgba(0,0,0,0)', color: colors.muted, activecolor: colors.accent };

  // Legend to the right side of the plot
  const legend = (layout.legend ?? {}) as Record<string, unknown>;
  legend.x = 1.02;
  legend.xanchor = 'left';
  legend.y = 1;
  legend.yanchor = 'top';
  delete legend.bgcolor;
  legend.traceorder = 'normal';
  legend.font = { size: 8, color: colors.muted };
  layout.legend = legend;

  // Compact margins with room for side legend
  const hasY2 = Object.keys(layout).some(k => k === 'yaxis2');
  const margin = (layout.margin ?? {}) as Record<string, unknown>;
  margin.t = 18;
  margin.b = 24;
  margin.l = 36;
  margin.r = hasY2 ? 100 : 70;
  layout.margin = margin;

  // Small bold title
  const title = layout.title as Record<string, unknown> | string | undefined;
  if (title && typeof title === 'object') {
    const titleFont = (title.font ?? {}) as Record<string, unknown>;
    titleFont.size = 10;
    titleFont.color = colors.text;
    title.font = titleFont;
  }

  // Override axis colors and fonts for dark theme
  for (const key of Object.keys(layout)) {
    if (key.startsWith('xaxis') || key.startsWith('yaxis')) {
      const axis = layout[key] as Record<string, unknown> | undefined;
      if (axis && typeof axis === 'object') {
        axis.gridcolor = `${colors.surface}66`;
        axis.zerolinecolor = `${colors.surface}99`;
        const axTitle = axis.title as Record<string, unknown> | undefined;
        if (axTitle && typeof axTitle === 'object') {
          const axTitleFont = (axTitle.font ?? {}) as Record<string, unknown>;
          axTitleFont.color = colors.muted;
          axTitleFont.size = 9;
          axTitle.font = axTitleFont;
        }
        axis.tickfont = { size: 8, color: colors.muted };
      }
    }
  }

  // Override annotation colors and sizes
  const annotations = layout.annotations as Record<string, unknown>[] | undefined;
  if (Array.isArray(annotations)) {
    for (const ann of annotations) {
      const annFont = (ann.font ?? {}) as Record<string, unknown>;
      if (!annFont.color) annFont.color = colors.text;
      annFont.size = Math.min(Number(annFont.size ?? 8), 8);
      ann.font = annFont;
    }
  }

  await Plotly.newPlot(el, spec.data as Plotly.Data[], layout as Partial<Plotly.Layout>, {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
  });
}

/**
 * Re-render a requirement plot with updated limits.
 * Creates a modified copy of req with new min/max and re-evaluates pass/fail.
 * Used for instant feedback when editing bounds — no simulation rerun needed.
 */
export async function rerenderWithLimits(
  container: HTMLDivElement,
  req: RequirementData,
  newMin: number,
  newMax: number,
  dim: { width: number; height: number },
): Promise<RequirementData> {
  const updated = {
    ...req,
    minVal: newMin,
    maxVal: newMax,
    passed: req.actual !== null && isFinite(req.actual) && newMin <= req.actual && req.actual <= newMax,
  };
  await renderRequirementPlot(container, updated, dim);
  return updated;
}

/** Extract the y-data extent from trace data arrays (primary y-axis only). */
function traceYExtent(data: Record<string, unknown>[]): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const trace of data) {
    // Skip traces on secondary y-axis
    if (trace.yaxis && trace.yaxis !== 'y') continue;
    const yArr = trace.y;
    if (Array.isArray(yArr)) {
      for (const v of yArr) {
        if (typeof v === 'number' && isFinite(v)) {
          if (v < lo) lo = v;
          if (v > hi) hi = v;
        }
      }
    }
  }
  return [lo, hi];
}

/**
 * Inject/replace limit shapes in a pre-built plotSpec using req.minVal/maxVal.
 * Strips existing Python-generated limit shapes (red lines, green rects) and
 * adds fresh ones matching the current requirement bounds.
 * Returns a new spec object (does not mutate the original).
 */
export function injectLimitShapes(
  spec: { data: Record<string, unknown>[]; layout: Record<string, unknown> },
  req: RequirementData,
): { data: Record<string, unknown>[]; layout: Record<string, unknown> } {
  // When we skip limit injection (no valid limits, or supplementary without
  // plot_limits), ensure the y-axis auto-fits all data by removing any
  // explicit range the Python spec may have set and enabling autorange.
  const ensureAutorange = (s: typeof spec) => {
    const cloned = JSON.parse(JSON.stringify(s)) as typeof spec;
    const [dMin, dMax] = traceYExtent(cloned.data);
    if (isFinite(dMin) && isFinite(dMax)) {
      const span = dMax - dMin || Math.abs(dMax) || 1;
      const pad = span * 0.1;
      (cloned.layout.yaxis as Record<string, unknown>).range = [dMin - pad, dMax + pad];
    } else {
      delete (cloned.layout.yaxis as Record<string, unknown>).range;
      (cloned.layout.yaxis as Record<string, unknown>).autorange = true;
    }
    return cloned;
  };

  if (req.minVal == null || req.maxVal == null) return ensureAutorange(spec);
  if (!isFinite(req.minVal) || !isFinite(req.maxVal)) return ensureAutorange(spec);

  // Supplementary plots: no limits unless explicitly opted in via plot_limits
  const meta = (spec as Record<string, unknown>).meta as PlotMeta | undefined;
  if (meta?.role === 'supplementary') {
    const pl = meta.plot_limits?.toLowerCase();
    if (pl !== 'true' && pl !== '1' && pl !== 'yes' && pl !== 'on') {
      return ensureAutorange(spec);
    }
  }

  const cloned: { data: Record<string, unknown>[]; layout: Record<string, unknown> } =
    JSON.parse(JSON.stringify(spec));
  const layout = cloned.layout;

  // Helper: check if an xref/yref is a "spanning" ref that indicates a limit shape.
  // Plotly uses 'paper' (older) or 'x domain'/'y domain' (newer) for full-span refs.
  const isSpanRef = (ref: unknown): boolean =>
    ref === 'paper' || (typeof ref === 'string' && ref.endsWith(' domain'));

  // Strip ALL existing limit shapes: pass-band rects, dotted limit lines, and
  // legacy red limit lines.
  const existingShapes = (layout.shapes ?? []) as Record<string, unknown>[];
  layout.shapes = existingShapes.filter((s: Record<string, unknown>) => {
    const line = s.line as Record<string, unknown> | undefined;
    const dash = line?.dash;
    // Pass-band rect: rect with a spanning ref on either axis
    if (s.type === 'rect' && (isSpanRef(s.xref) || isSpanRef(s.yref))) return false;
    // Dotted limit lines with a spanning ref
    if (s.type === 'line' && (isSpanRef(s.xref) || isSpanRef(s.yref)) && dash === 'dot') return false;
    // Legacy red limit lines
    if (s.type === 'line' && line?.color === 'red' && (isSpanRef(s.xref) || isSpanRef(s.yref))) return false;
    return true;
  });

  // Strip ALL limit annotations (LSL/USL labels)
  const existingAnns = (layout.annotations ?? []) as Record<string, unknown>[];
  layout.annotations = existingAnns.filter((a: Record<string, unknown>) => {
    const txt = typeof a.text === 'string' ? a.text : '';
    if (txt.includes('LSL') || txt.includes('USL')) return false;
    return true;
  });

  const colors = themeColors();
  const shapes = layout.shapes as Record<string, unknown>[];
  const anns = layout.annotations as Record<string, unknown>[];

  // Detect if this is a bar/measurement chart vs a waveform
  const isBarChart = cloned.data.some(
    (t: Record<string, unknown>) => t.type === 'bar',
  );

  if (req.measurement === 'peak_to_peak' && !isBarChart) {
    // P-P on waveform: draw envelope at center ± limit/2
    let center = 0;
    const mainTrace = cloned.data[0];
    if (mainTrace && Array.isArray(mainTrace.y)) {
      const yData = mainTrace.y as number[];
      if (yData.length > 0) {
        center = (Math.max(...yData) + Math.min(...yData)) / 2;
      }
    }
    const halfMax = req.maxVal / 2;
    shapes.push(
      { type: 'rect', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: center - halfMax, y1: center + halfMax, fillcolor: `${colors.success}14`, line: { width: 0 } },
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: center + halfMax, y1: center + halfMax, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: center - halfMax, y1: center - halfMax, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
    );
    anns.push(
      { x: 0.02, y: center + halfMax, xref: 'paper', yref: 'y', text: `USL ±${formatEng(halfMax, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'bottom' },
      { x: 0.02, y: center - halfMax, xref: 'paper', yref: 'y', text: `USL ±${formatEng(halfMax, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'top' },
    );
    if (req.minVal > 0 && Math.abs(req.minVal - req.maxVal) > 1e-12) {
      const halfMin = req.minVal / 2;
      shapes.push(
        { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: center + halfMin, y1: center + halfMin, line: { color: colors.muted, width: 1, dash: 'dot' } },
        { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: center - halfMin, y1: center - halfMin, line: { color: colors.muted, width: 1, dash: 'dot' } },
      );
      anns.push(
        { x: 0.02, y: center + halfMin, xref: 'paper', yref: 'y', text: `LSL ±${formatEng(halfMin, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'bottom' },
        { x: 0.02, y: center - halfMin, xref: 'paper', yref: 'y', text: `LSL ±${formatEng(halfMin, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'top' },
      );
    }
    // Set y-axis range to include both limits AND all data
    const usl = center + halfMax;
    const lsl = center - halfMax;
    const [ppDataMin, ppDataMax] = traceYExtent(cloned.data);
    const ppVisMin = isFinite(ppDataMin) ? Math.min(lsl, ppDataMin) : lsl;
    const ppVisMax = isFinite(ppDataMax) ? Math.max(usl, ppDataMax) : usl;
    const limitSpan = ppVisMax - ppVisMin;
    const pad = limitSpan * 0.1;
    (layout.yaxis as Record<string, unknown>).range = [ppVisMin - pad, ppVisMax + pad];
  } else {
    // Standard: horizontal limits at min/max
    shapes.push(
      { type: 'rect', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: req.minVal, y1: req.maxVal, fillcolor: `${colors.success}14`, line: { width: 0 } },
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: req.minVal, y1: req.minVal, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: req.maxVal, y1: req.maxVal, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
    );
    anns.push(
      { x: 0.02, y: req.minVal, xref: 'paper', yref: 'y', text: `LSL ${formatEng(req.minVal, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'bottom' },
      { x: 0.02, y: req.maxVal, xref: 'paper', yref: 'y', text: `USL ${formatEng(req.maxVal, req.unit)}`, showarrow: false, font: { size: 7, color: colors.muted }, xanchor: 'left', yanchor: 'top' },
    );
    // Set y-axis range to include both limits AND all data
    const [dataMin, dataMax] = traceYExtent(cloned.data);
    const visibleMin = isFinite(dataMin) ? Math.min(req.minVal, dataMin) : req.minVal;
    const visibleMax = isFinite(dataMax) ? Math.max(req.maxVal, dataMax) : req.maxVal;
    const stdSpan = visibleMax - visibleMin;
    const stdPad = stdSpan * 0.1;
    (layout.yaxis as Record<string, unknown>).range = [visibleMin - stdPad, visibleMax + stdPad];
  }

  return cloned;
}

/**
 * Apply a plot field change to a PlotSpec's layout/meta.
 * Returns a deep-cloned spec with the change applied, suitable for re-rendering.
 *
 * For `y` / `y_secondary` changes, rebuilds traces from timeSeries data if available.
 * For `title`, updates layout.title.text directly.
 */
export function applyPlotFieldToSpec<T extends { data: Record<string, unknown>[]; layout: Record<string, unknown> }>(
  spec: T,
  field: string,
  value: string,
  timeSeries?: { time: number[]; signals: Record<string, number[]> } | null,
): T {
  const cloned: T = JSON.parse(JSON.stringify(spec));

  // Update meta if present
  const meta = (cloned as Record<string, unknown>).meta as Record<string, unknown> | undefined;
  if (meta) {
    meta[field] = value;
  }

  // Apply to layout where possible
  if (field === 'title') {
    const layout = cloned.layout;
    const existing = layout.title as Record<string, unknown> | undefined;
    if (existing && typeof existing === 'object') {
      const oldText = typeof existing.text === 'string' ? existing.text : '';
      const badgeMatch = oldText.match(/(\s*<span style='color:#[0-9a-f]+.*?\[(?:PASS|FAIL)\]<\/span>.*)/i);
      existing.text = `<b>${value}</b>${badgeMatch ? badgeMatch[1] : ''}`;
    } else {
      layout.layout = { text: `<b>${value}</b>`, x: 0.5, font: { size: 16 } };
    }
  }

  // Rebuild traces from timeSeries when y-axis changes
  if ((field === 'y' || field === 'y_secondary') && timeSeries && value) {
    const allY = meta?.y as string | undefined;
    const allYSec = meta?.y_secondary as string | undefined;

    // Determine which signals to show on primary and secondary axes
    const primarySignals = field === 'y' ? value : (allY ?? '');
    const secondarySignals = field === 'y_secondary' ? value : (allYSec ?? '');

    // Rebuild the data traces array from timeSeries
    const newTraces: Record<string, unknown>[] = [];
    const timeData = timeSeries.time;

    // Helper to resolve a signal spec to a timeSeries key
    const resolveSignal = (sigSpec: string): { key: string; data: number[] } | null => {
      // Direct match: v(net) or i(element)
      if (sigSpec in timeSeries.signals) return { key: sigSpec, data: timeSeries.signals[sigSpec] };
      // Try wrapping in v()
      const vKey = `v(${sigSpec})`;
      if (vKey in timeSeries.signals) return { key: vKey, data: timeSeries.signals[vKey] };
      // Try with dots replaced by underscores (net alias convention)
      const underscored = sigSpec.replace(/\./g, '_');
      const vKeyU = `v(${underscored})`;
      if (vKeyU in timeSeries.signals) return { key: vKeyU, data: timeSeries.signals[vKeyU] };
      // Try as current probe
      const iKey = `i(${sigSpec})`;
      if (iKey in timeSeries.signals) return { key: iKey, data: timeSeries.signals[iKey] };
      // Fuzzy: find a signal key containing the spec
      for (const [k, d] of Object.entries(timeSeries.signals)) {
        if (k.includes(sigSpec) || k.includes(underscored)) return { key: k, data: d };
      }
      return null;
    };

    // Add primary traces
    for (const sig of primarySignals.split(',').map(s => s.trim()).filter(Boolean)) {
      const resolved = resolveSignal(sig);
      if (resolved) {
        newTraces.push({
          x: timeData,
          y: resolved.data,
          mode: 'lines',
          name: formatSignalName(resolved.key),
          type: 'scatter',
        });
      }
    }

    // Add secondary traces (dashed, on yaxis2)
    for (const sig of secondarySignals.split(',').map(s => s.trim()).filter(Boolean)) {
      const resolved = resolveSignal(sig);
      if (resolved) {
        newTraces.push({
          x: timeData,
          y: resolved.data,
          mode: 'lines',
          name: formatSignalName(resolved.key),
          type: 'scatter',
          yaxis: 'y2',
          line: { width: 0.75 },
        });
      }
    }

    if (newTraces.length > 0) {
      cloned.data = newTraces as T['data'];

      // Ensure yaxis2 exists in layout if we have secondary traces
      if (secondarySignals) {
        cloned.layout.yaxis2 = {
          overlaying: 'y',
          side: 'right',
          showgrid: false,
        };
      }
    }
  }

  return cloned;
}

export async function purgePlot(el: HTMLDivElement) {
  const Plotly = await getPlotly();
  Plotly.purge(el);
}

export async function resizePlot(el: HTMLDivElement) {
  const Plotly = await getPlotly();
  const dim = fixedDimensions();
  Plotly.relayout(el, { width: dim.width, height: dim.height });
}

/**
 * Unified plot renderer for a single requirement.
 * Clears `container`, creates child wrappers, and renders using plotSpecs
 * (preferred) or falls back to measurement-specific renderers.
 * Used by RequirementsAllPage.
 */
export async function renderRequirementPlot(
  container: HTMLDivElement,
  req: RequirementData,
  dim: { width: number; height: number },
): Promise<void> {
  // Clear previous content
  const oldChildren = Array.from(container.children) as HTMLDivElement[];
  for (const child of oldChildren) {
    try { purgePlot(child); } catch { /* ignore */ }
  }
  container.innerHTML = '';

  if (req.plotSpecs && req.plotSpecs.length > 0) {
    for (const spec of req.plotSpecs) {
      const wrapper = document.createElement('div');
      wrapper.style.width = `${dim.width}px`;
      wrapper.style.height = `${dim.height}px`;
      container.appendChild(wrapper);
      await renderSpecAtSize(wrapper as HTMLDivElement, spec, dim.width, dim.height);
    }
  } else {
    const chartEl = document.createElement('div');
    chartEl.style.width = `${dim.width}px`;
    chartEl.style.height = `${dim.height}px`;
    container.appendChild(chartEl);

    if (req.sweepPoints && req.sweepPoints.length > 0) {
      await renderSweepPlot(chartEl as HTMLDivElement, req, dim);
    } else if (req.frequencySeries) {
      await renderBodePlot(chartEl as HTMLDivElement, req, dim);
    } else if (req.timeSeries) {
      await renderTransientPlot(chartEl as HTMLDivElement, req, dim);
    } else {
      await renderDCPlot(chartEl as HTMLDivElement, req, dim);
    }
  }
}
