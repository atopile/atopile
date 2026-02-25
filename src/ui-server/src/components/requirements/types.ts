/** Data shape for a single simulation requirement result */
export interface RequirementData {
  id: string;
  name: string;
  net: string;
  capture: 'dcop' | 'transient' | 'ac';
  measurement: string;
  minVal: number;
  typical: number;
  maxVal: number;
  actual: number | null;
  passed: boolean;
  justification?: string;
  displayNet?: string;
  contextNets: string[];
  unit: string;
  settlingTolerance?: number;
  tranStart?: number;
  tranStop?: number;
  tranStep?: number;
  timeSeries: TimeSeriesData | null;
  frequencySeries: FrequencySeriesData | null;
  sweepPoints?: SweepPointData[];
  sweepParamName?: string;
  sweepParamUnit?: string;
  /** AC analysis configuration */
  acStartFreq?: number;
  acStopFreq?: number;
  acPointsPerDec?: number;
  acSourceName?: string;
  acMeasureFreq?: number;
  acRefNet?: string;
  /** Pre-rendered Plotly figure specs from Python — each has data + layout + meta */
  plotSpecs?: PlotSpec[];
  /** Path to the .ato source file (for UI editing) */
  sourceFile?: string;
  /** Variable name of this requirement in the .ato source (for UI editing) */
  varName?: string;
  /** Original limit expression from .ato source, e.g. "5V +/- 10%" or "0s to 5ms" */
  limitExpr?: string;
  /** Path to the .spice netlist file (for single-sim rerun) */
  netlistPath?: string;
  /** Simulation name override */
  simulationName?: string;
  /** SPICE source override name (e.g. "V1") */
  sourceName?: string;
  /** SPICE source override spec (e.g. "PULSE(0 12 0 10u 10u 10 10)") */
  sourceSpec?: string;
  /** Extra SPICE commands */
  extraSpice?: string[];
  /** SPICE source definition from Simulation node */
  spice?: string;
}

/** A single Plotly plot spec with optional editing metadata */
export interface PlotSpec {
  data: Record<string, unknown>[];
  layout: Record<string, unknown>;
  meta?: PlotMeta;
}

/** Metadata for an editable plot — matches LineChart/BarChart fields in .ato */
export interface PlotMeta {
  varName?: string;
  plotType?: string;
  title?: string;
  x?: string;
  y?: string;
  y_secondary?: string;
  color?: string;
  simulation?: string;
  plot_limits?: string;
}

/** A single sweep data point */
export interface SweepPointData {
  paramValue: number;
  actual: number;
  passed: boolean;
}

/** Time-domain simulation data */
export interface TimeSeriesData {
  time: number[];
  signals: Record<string, number[]>;
}

/** Frequency-domain simulation data (AC analysis) */
export interface FrequencySeriesData {
  freq: number[];
  gain_db: number[];
  phase_deg: number[];
}

/** Per-simulation timing data */
export interface SimStatData {
  name: string;
  simType: string;
  elapsedS: number;
  dataPoints: number;
}

/** Top-level container returned from backend */
export interface RequirementsData {
  requirements: RequirementData[];
  buildTime: string;
  simStats?: SimStatData[];
}

export type FilterType = 'all' | 'pass' | 'fail' | 'dc' | 'transient' | 'ac';
