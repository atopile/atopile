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
  timeSeries: TimeSeriesData | null;
  frequencySeries: FrequencySeriesData | null;
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

/** Top-level container returned from backend */
export interface RequirementsData {
  requirements: RequirementData[];
  buildTime: string;
}

export type FilterType = 'all' | 'pass' | 'fail' | 'dc' | 'transient' | 'ac';
