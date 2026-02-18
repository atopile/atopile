/** Data shape for a single simulation requirement result */
export interface RequirementData {
  id: string;
  name: string;
  net: string;
  capture: 'dcop' | 'transient';
  measurement: string;
  minVal: number;
  typical: number;
  maxVal: number;
  actual: number;
  passed: boolean;
  justification?: string;
  contextNets: string[];
  unit: string;
  settlingTolerance?: number;
  tranStart?: number;
  tranStop?: number;
  timeSeries: TimeSeriesData | null;
}

/** Time-domain simulation data */
export interface TimeSeriesData {
  time: number[];
  signals: Record<string, number[]>;
}

/** Top-level container returned from backend */
export interface RequirementsData {
  requirements: RequirementData[];
  buildTime: string;
}

export type FilterType = 'all' | 'pass' | 'fail' | 'dc' | 'transient';
