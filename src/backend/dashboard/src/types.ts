export interface ServiceCard {
  service: string;
  status: string;
  requests: number;
  requests_per_min: number;
  p50_ms: number;
  p95_ms: number;
  error_rate_pct: number;
  success_rate_pct: number;
}

export interface TimelinePoint {
  timestamp: string;
  requests_per_min: number;
  p95_ms: number;
  error_count: number;
}

export interface RouteStat {
  route: string;
  count: number;
  p95_ms: number;
  error_rate_pct: number;
}

export interface CountRow {
  count: number;
}

export interface ComponentDemand extends CountRow {
  component_type: string;
}

export interface PackageCount extends CountRow {
  package: string;
}

export interface OriginPoint {
  id: string;
  label: string;
  country: string;
  lat: number;
  lon: number;
  count: number;
  request_share_pct: number;
  geo_source: string;
}

export interface HttpSummary {
  total_requests: number;
  success_count: number;
  client_errors: number;
  server_errors: number;
  requests_per_min: number;
  p50_ms: number;
  p95_ms: number;
  error_rate_pct: number;
  success_rate_pct: number;
  requests_timeline: TimelinePoint[];
}

export interface SnapshotPackageStats {
  total_components?: number;
  component_type_counts?: Record<string, number>;
  distinct_packages?: number;
  distinct_packages_by_component_type?: Record<string, number>;
  top_packages?: Array<{
    package: string;
    part_count: number;
  }>;
}

export interface DashboardMetricsResponse {
  generated_at_utc: string;
  window_seconds: number;
  uptime_seconds: number;
  services: ServiceCard[];
  http: HttpSummary;
  top_routes: RouteStat[];
  component_demand: ComponentDemand[];
  component_zero_results?: ComponentDemand[];
  package_hits: PackageCount[];
  package_returns: PackageCount[];
  origins: OriginPoint[];
  snapshot_package_stats: SnapshotPackageStats;
}
