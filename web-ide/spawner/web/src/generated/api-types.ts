// Generated from Pydantic models. Do not edit by hand.

export interface HealthResponse {
  ok: boolean;
  sessions: number;
  pool: number;
  max_machine_count: number | null;
  uptime: number;
}

export interface ErrorResponse {
  error: string;
}

export interface DashboardPoint {
  timestamp_ms: number;
  active: number;
  warm: number;
  total: number;
}

export interface DashboardSeriesResponse {
  points: DashboardPoint[];
  active: number;
  warm: number;
  total: number;
  max_machine_count: number | null;
}
