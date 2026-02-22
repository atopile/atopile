import type { RequirementData } from './types';
import { formatEng, autoScaleTime } from './helpers';

type Plotly = typeof import('plotly.js-basic-dist-min');

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
    info: get('--info', '#89b4fa'),
    accent: get('--accent', '#f95015'),
  };
}

const MAX_CHART_HEIGHT = 500;
const MIN_CHART_HEIGHT = 300;

/** Compute width/height for a 16:9 plot that fits inside the container.
 *  Reads dimensions from the parent wrapper (`.rdp-chart`), not the chart div itself.
 *  Never shrinks below MIN_CHART_HEIGHT — the container clips the overflow instead. */
function fitDimensions(chartEl: HTMLElement): { width: number; height: number } {
  const container = chartEl.parentElement ?? chartEl;
  const style = getComputedStyle(container);
  const padX = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
  const w = container.clientWidth - padX;
  const targetH = Math.max(Math.min(w * 9 / 16, MAX_CHART_HEIGHT), MIN_CHART_HEIGHT);
  const targetW = targetH * 16 / 9;
  return { width: Math.min(w, targetW), height: targetH };
}

function baseLayout(colors: ReturnType<typeof themeColors>) {
  return {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: '-apple-system, sans-serif', color: colors.text, size: 11 },
    margin: { t: 40, r: 40, b: 100, l: 65 },
    xaxis: {
      gridcolor: `${colors.surface}66`,
      zerolinecolor: `${colors.surface}99`,
      title: { text: '', font: { size: 11, color: colors.muted } },
      tickfont: { size: 10 },
    },
    yaxis: {
      gridcolor: `${colors.surface}66`,
      zerolinecolor: `${colors.surface}99`,
      title: { text: '', font: { size: 11, color: colors.muted } },
      tickfont: { size: 10 },
    },
    legend: { x: 0.5, xanchor: 'center' as const, y: -0.35, orientation: 'h' as const, font: { size: 10, color: colors.muted } },
    modebar: { bgcolor: 'rgba(0,0,0,0)', color: colors.muted, activecolor: colors.accent },
  };
}

export async function renderTransientPlot(el: HTMLDivElement, req: RequirementData) {
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

  const nutLabel = (req as any).displayNet || netKey;
  traces.push({
    x: timeScaled,
    y: nutSignal,
    type: 'scatter',
    mode: 'lines',
    name: nutLabel,
    line: { color: colors.info, width: 2 },
  });

  const ctxColors = ['#fab387', '#a6e3a1', '#cba6f7', '#eba0ac'];
  (req.contextNets || []).forEach((cn, i) => {
    const ck = cn.startsWith('v(') || cn.startsWith('i(') ? cn : `v(${cn})`;
    if (ts.signals[ck]) {
      traces.push({
        x: timeScaled,
        y: ts.signals[ck],
        type: 'scatter',
        mode: 'lines',
        name: ck,
        line: { color: ctxColors[i % ctxColors.length], width: 1.5 },
        yaxis: 'y2',
      });
    }
  });

  const dim = fitDimensions(el);
  const layout: Record<string, unknown> = {
    ...baseLayout(colors),
    width: dim.width,
    height: dim.height,
    title: { text: `<b>${req.name}</b> — ${req.measurement.replace(/_/g, ' ')}`, font: { size: 13, color: colors.text } },
    xaxis: { ...baseLayout(colors).xaxis, title: { text: `Time (${tUnit})`, font: { size: 11, color: colors.muted } } },
    yaxis: { ...baseLayout(colors).yaxis, title: { text: (() => {
      // For measurements where the result unit differs from the signal unit,
      // show the signal unit (V/A) on the y-axis, not the measurement unit
      if (req.unit === '%' ) return '%';
      if (['frequency', 'settling_time'].includes(req.measurement)) {
        return req.net.startsWith('i(') ? 'A' : 'V';
      }
      return req.unit;
    })(), font: { size: 11, color: colors.muted } } },
    shapes: [] as Record<string, unknown>[],
    annotations: [] as Record<string, unknown>[],
  };

  if (req.contextNets && req.contextNets.length > 0) {
    layout.yaxis2 = {
      ...baseLayout(colors).yaxis,
      title: { text: 'Context', font: { size: 11, color: colors.muted } },
      overlaying: 'y',
      side: 'right',
    };
    (layout.margin as Record<string, number>).r = 60;
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
      { x: 0.02, y: req.minVal, xref: 'paper', yref: 'y', text: `LSL ${formatEng(req.minVal, req.unit)}`, showarrow: false, font: { size: 9, color: colors.muted }, xanchor: 'left', yanchor: 'bottom' },
      { x: 0.02, y: req.maxVal, xref: 'paper', yref: 'y', text: `USL ${formatEng(req.maxVal, req.unit)}`, showarrow: false, font: { size: 9, color: colors.muted }, xanchor: 'left', yanchor: 'top' },
      { x: 0.98, y: req.actual ?? 0, xref: 'paper', yref: 'y', text: `${formatEng(req.actual ?? NaN, req.unit)}`, showarrow: false, font: { size: 10, color: req.passed ? colors.success : colors.error }, xanchor: 'right', yanchor: 'bottom' },
    );
    const span = req.maxVal - req.minVal;
    const pad = span * 0.5;
    (layout.yaxis as Record<string, unknown>).range = [req.minVal - pad, req.maxVal + pad];
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
      showarrow: false, font: { size: 10, color: req.passed ? colors.success : colors.error },
      textangle: -90, xanchor: 'left', xshift: 6,
    });
    const pad = band * 2;
    (layout.yaxis as Record<string, unknown>).range = [final - band - pad, final + band + pad];
  }

  if (req.measurement === 'peak_to_peak') {
    const peak = Math.max(...nutSignal);
    const trough = Math.min(...nutSignal);
    shapes.push(
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: peak, y1: peak, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: trough, y1: trough, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
    );
    annotations.push({
      x: 0.95, y: (peak + trough) / 2, xref: 'paper', yref: 'y',
      text: `P-P: ${formatEng(req.actual ?? NaN, req.unit)}`,
      showarrow: false, font: { size: 11, color: colors.text },
      bgcolor: 'rgba(0,0,0,0.6)', borderpad: 3,
    });
    const span = peak - trough;
    const pad = span * 0.2;
    (layout.yaxis as Record<string, unknown>).range = [trough - pad, peak + pad];
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
      { x: 0.02, y: final, xref: 'paper', yref: 'y', text: `Final ${formatEng(final, 'V')}`, showarrow: false, font: { size: 9, color: colors.muted }, xanchor: 'left', yanchor: 'top' },
      { x: 0.02, y: maxOsV, xref: 'paper', yref: 'y', text: `Max OS ${req.maxVal}%`, showarrow: false, font: { size: 9, color: colors.muted }, xanchor: 'left', yanchor: 'bottom' },
      { x: peakTime, y: peak, xref: 'x', yref: 'y', text: `OS: ${(req.actual ?? 0).toFixed(2)}%`, showarrow: true, ay: -25, arrowcolor: colors.error, arrowwidth: 1.5, font: { size: 11, color: colors.error } },
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

export async function renderDCPlot(el: HTMLDivElement, req: RequirementData) {
  const Plotly = await getPlotly();
  const colors = themeColors();
  const range = req.maxVal - req.minVal;
  const padding = range * 0.3;

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
    name: 'Actual',
  }];

  const dim = fitDimensions(el);
  const layout = {
    ...baseLayout(colors),
    width: dim.width,
    height: dim.height,
    title: { text: `<b>${req.name}</b> — ${req.measurement.replace(/_/g, ' ')}`, font: { size: 13, color: colors.text } },
    xaxis: {
      ...baseLayout(colors).xaxis,
      title: { text: req.unit, font: { size: 11, color: colors.muted } },
      range: [req.minVal - padding, req.maxVal + padding],
    },
    yaxis: { visible: false, fixedrange: true },
    shapes: [
      { type: 'rect', xref: 'x', yref: 'paper', x0: req.minVal, x1: req.maxVal, y0: 0, y1: 1, fillcolor: `${colors.success}1A`, line: { width: 0 } },
      { type: 'line', xref: 'x', yref: 'paper', x0: req.minVal, x1: req.minVal, y0: 0, y1: 1, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'x', yref: 'paper', x0: req.maxVal, x1: req.maxVal, y0: 0, y1: 1, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'x', yref: 'paper', x0: req.typical, x1: req.typical, y0: 0, y1: 1, line: { color: colors.muted, width: 1, dash: 'dash' } },
    ],
    annotations: [
      { x: req.minVal, y: 1.05, xref: 'x', yref: 'paper', text: 'LSL', showarrow: false, font: { size: 9, color: colors.muted } },
      { x: req.maxVal, y: 1.05, xref: 'x', yref: 'paper', text: 'USL', showarrow: false, font: { size: 9, color: colors.muted } },
      { x: req.actual ?? 0, y: -0.15, xref: 'x', yref: 'paper', text: formatEng(req.actual ?? NaN, req.unit), showarrow: false, font: { size: 11, color: req.passed ? colors.success : colors.error } },
    ],
  };

  Plotly.newPlot(el, traces, layout as Partial<Plotly.Layout>, {
    responsive: true,
    displaylogo: false,
    staticPlot: true,
  });
}

export async function renderBodePlot(el: HTMLDivElement, req: RequirementData) {
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
    line: { color: '#fab387', width: 2 },
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

  const dim = fitDimensions(el);
  const layout: Record<string, unknown> = {
    ...baseLayout(colors),
    width: dim.width,
    height: dim.height,
    title: { text: `<b>${req.name}</b> — ${req.measurement.replace(/_/g, ' ')}`, font: { size: 13, color: colors.text } },
    xaxis: {
      ...baseLayout(colors).xaxis,
      type: 'log',
      title: { text: 'Frequency (Hz)', font: { size: 11, color: colors.muted } },
    },
    yaxis: {
      ...baseLayout(colors).yaxis,
      title: { text: 'Gain (dB)', font: { size: 11, color: colors.info } },
    },
    yaxis2: {
      ...baseLayout(colors).yaxis,
      title: { text: 'Phase (deg)', font: { size: 11, color: '#fab387' } },
      overlaying: 'y',
      side: 'right',
    },
    shapes: [] as Record<string, unknown>[],
    annotations: [] as Record<string, unknown>[],
  };
  (layout.margin as Record<string, number>).r = 60;

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
      xshift: 8, yshift: -4,
      font: { size: 10, color: '#000' },
    });
  }

  Plotly.newPlot(el, traces, layout as Partial<Plotly.Layout>, {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
  });
}

export async function renderSweepPlot(el: HTMLDivElement, req: RequirementData) {
  const Plotly = await getPlotly();
  const colors = themeColors();
  const pts = req.sweepPoints!;
  const xVals = pts.map(p => p.paramValue);
  const yVals = pts.map(p => p.actual);
  const ptColors = pts.map(p => p.passed ? colors.success : colors.error);

  const dim = fitDimensions(el);
  const layout: Record<string, unknown> = {
    ...baseLayout(colors),
    width: dim.width,
    height: dim.height,
    title: { text: `<b>${req.name}</b> — sweep`, font: { size: 13, color: colors.text } },
    xaxis: { ...baseLayout(colors).xaxis, title: { text: req.sweepParamName || 'Parameter', font: { size: 11, color: colors.muted } } },
    yaxis: { ...baseLayout(colors).yaxis, title: { text: req.unit, font: { size: 11, color: colors.muted } } },
    shapes: [
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: req.minVal, y1: req.minVal, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
      { type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: req.maxVal, y1: req.maxVal, line: { color: colors.muted, width: 1.5, dash: 'dot' } },
    ],
  };

  Plotly.newPlot(el, [{
    x: xVals, y: yVals, type: 'scatter', mode: 'lines+markers',
    marker: { size: 8, color: ptColors },
    line: { color: colors.info, width: 2 },
    name: 'Measured',
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
  layout.font = font;

  layout.modebar = { bgcolor: 'rgba(0,0,0,0)', color: colors.muted, activecolor: colors.accent };

  // Override legend: move to the right side
  const legend = (layout.legend ?? {}) as Record<string, unknown>;
  const legendFont = (legend.font ?? {}) as Record<string, unknown>;
  legendFont.color = colors.muted;
  legend.font = legendFont;
  legend.x = 1.02;
  legend.xanchor = 'left';
  legend.y = 1;
  legend.yanchor = 'top';
  layout.legend = legend;

  // Ensure right margin has room for the legend
  const margin = (layout.margin ?? {}) as Record<string, unknown>;
  margin.r = Math.max(Number(margin.r ?? 0), 140);
  layout.margin = margin;

  // Override axis colors for dark theme
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
          axTitle.font = axTitleFont;
        }
        const tickFont = (axis.tickfont ?? {}) as Record<string, unknown>;
        tickFont.color = colors.muted;
        axis.tickfont = tickFont;
      }
    }
  }

  // Override annotation colors
  const annotations = layout.annotations as Record<string, unknown>[] | undefined;
  if (Array.isArray(annotations)) {
    for (const ann of annotations) {
      const annFont = (ann.font ?? {}) as Record<string, unknown>;
      if (!annFont.color) annFont.color = colors.text;
      ann.font = annFont;
    }
  }

  await Plotly.newPlot(el, spec.data as Plotly.Data[], layout as Partial<Plotly.Layout>, {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
  });
}

export async function purgePlot(el: HTMLDivElement) {
  const Plotly = await getPlotly();
  Plotly.purge(el);
}

export async function resizePlot(el: HTMLDivElement) {
  const Plotly = await getPlotly();
  const dim = fitDimensions(el);
  Plotly.relayout(el, { width: dim.width, height: dim.height });
}
