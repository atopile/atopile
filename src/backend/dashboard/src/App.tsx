import { useEffect, useMemo, useState } from "react";

import { BarList } from "./components/BarList";
import { CorrelationChart } from "./components/CorrelationChart";
import { LatencyChart } from "./components/LatencyChart";
import { MiniTrendCard } from "./components/MiniTrendCard";
import { ServiceRail } from "./components/ServiceRail";
import {
  formatCompactNumber,
  formatMs,
  formatPct,
  formatTimestamp,
  formatUptime
} from "./lib/format";
import type { DashboardMetricsResponse } from "./types";

const WINDOW_OPTIONS = [
  { label: "15m", seconds: 15 * 60 },
  { label: "1h", seconds: 60 * 60 },
  { label: "6h", seconds: 6 * 60 * 60 },
  { label: "24h", seconds: 24 * 60 * 60 }
] as const;

function trimRoute(route: string): string {
  if (route.length <= 36) {
    return route;
  }
  return `${route.slice(0, 33)}...`;
}

function useDashboardMetrics(
  windowSeconds: number
): {
  data: DashboardMetricsResponse | null;
  error: string | null;
  loading: boolean;
} {
  const [data, setData] = useState<DashboardMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function load(isInitialLoad: boolean): Promise<void> {
      if (isInitialLoad && isMounted) {
        setLoading(true);
      }

      try {
        const response = await fetch(
          `/v1/dashboard/metrics?window_seconds=${windowSeconds}`,
          {
            headers: {
              Accept: "application/json"
            }
          }
        );
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload = (await response.json()) as DashboardMetricsResponse;
        if (!isMounted) {
          return;
        }
        setData(payload);
        setError(null);
      } catch (fetchError) {
        if (!isMounted) {
          return;
        }
        const message =
          fetchError instanceof Error ? fetchError.message : "Unable to load metrics";
        setError(message);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void load(true);
    const timer = window.setInterval(() => {
      void load(false);
    }, 5_000);

    return () => {
      isMounted = false;
      window.clearInterval(timer);
    };
  }, [windowSeconds]);

  return { data, error, loading };
}

export default function App(): JSX.Element {
  const [windowSeconds, setWindowSeconds] = useState<number>(WINDOW_OPTIONS[0].seconds);
  const { data, error, loading } = useDashboardMetrics(windowSeconds);
  const timeline = data?.http.requests_timeline ?? [];

  const selectedWindowLabel =
    WINDOW_OPTIONS.find((option) => option.seconds === windowSeconds)?.label ?? "15m";

  const routeItems = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.top_routes.slice(0, 8).map((entry) => ({
      label: trimRoute(entry.route),
      count: entry.count,
      subtitle: `${formatMs(entry.p95_ms)} p95 • ${formatPct(entry.error_rate_pct)} 5xx`
    }));
  }, [data]);

  const componentInventoryItems = useMemo(() => {
    const rawCounts = data?.snapshot_package_stats.component_type_counts ?? {};
    return Object.entries(rawCounts)
      .map(([componentType, count]) => ({
        label: componentType,
        count
      }))
      .sort((left, right) => right.count - left.count)
      .slice(0, 8);
  }, [data]);

  const demandItems = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.component_demand.slice(0, 7).map((entry) => ({
      label: entry.component_type,
      count: entry.count
    }));
  }, [data]);

  const zeroResultItems = useMemo(() => {
    if (!data) {
      return [];
    }
    return (data.component_zero_results ?? []).slice(0, 7).map((entry) => ({
      label: entry.component_type,
      count: entry.count
    }));
  }, [data]);

  const packageHitItems = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.package_hits.slice(0, 7).map((entry) => ({
      label: entry.package,
      count: entry.count
    }));
  }, [data]);

  const packageReturnItems = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.package_returns.slice(0, 7).map((entry) => ({
      label: entry.package,
      count: entry.count
    }));
  }, [data]);

  const generatedAt = data ? formatTimestamp(data.generated_at_utc) : "--";
  const uptime = data ? formatUptime(data.uptime_seconds) : "--";
  const requestSeries = timeline.map((point) => point.requests_per_min);
  const latencySeries = timeline.map((point) => point.p95_ms);
  const errorSeries = timeline.map((point) => point.error_count);
  const stalenessMs = data ? Date.now() - new Date(data.generated_at_utc).getTime() : 0;
  const freshness = data ? (stalenessMs > 20_000 ? "Delayed" : "Live") : "--";
  const pipeline = data?.pipeline_status;
  const stage1Success = pipeline?.stage1.state_counts.success ?? 0;
  const stage1Failed = pipeline?.stage1.state_counts.failed ?? 0;
  const stage1Running = pipeline?.stage1.state_counts.running ?? 0;
  const stage2Components = Number(
    pipeline?.stage2.current.metadata?.source_component_count ?? 0
  );
  const snapshotName = String(
    pipeline?.stage2.current.metadata?.snapshot_name ?? "unpublished"
  );
  const assetTypeItems = (pipeline?.stage1.assets_by_type ?? [])
    .slice(0, 8)
    .map((entry) => ({
      label: entry.artifact_type,
      count: entry.artifact_count,
      subtitle: `${formatCompactNumber(entry.part_count)} parts`
    }));

  return (
    <main className="dashboard-root">
      <header className="dashboard-header card">
        <div>
          <p className="eyebrow">Atopile Components Backend</p>
          <h1>Observability Console</h1>
          <p className="header-subtitle">
            Real-time API health, latency, and demand diagnostics for component services.
          </p>
        </div>

        <div className="header-controls">
          <div className="window-picker" aria-label="Time window">
            {WINDOW_OPTIONS.map((option) => (
              <button
                key={option.seconds}
                type="button"
                className={option.seconds === windowSeconds ? "active" : ""}
                onClick={() => {
                  setWindowSeconds(option.seconds);
                }}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="header-meta">
            <div>
              <span>Status</span>
              <strong>{freshness}</strong>
            </div>
            <div>
              <span>Last sync</span>
              <strong>{generatedAt}</strong>
            </div>
            <div>
              <span>Window</span>
              <strong>{selectedWindowLabel}</strong>
            </div>
            <div>
              <span>Uptime</span>
              <strong>{uptime}</strong>
            </div>
          </div>
        </div>
      </header>

      {loading && !data ? <div className="card loading">Loading telemetry…</div> : null}
      {error ? <div className="card error">Dashboard API error: {error}</div> : null}

      {data ? (
        <>
          <ServiceRail services={data.services} />

          <section className="pipeline-flow" aria-label="Pipeline flow status">
            <article className="pipeline-stage card">
              <h3>Stage 1: Fetch</h3>
              <p className="pipeline-number">
                {formatCompactNumber(pipeline?.stage1.total_parts_seen ?? 0)} parts
              </p>
              <p className="pipeline-meta">
                ok {formatCompactNumber(stage1Success)} | fail{" "}
                {formatCompactNumber(stage1Failed)} | run{" "}
                {formatCompactNumber(stage1Running)}
              </p>
              <p className="pipeline-meta">
                artifacts{" "}
                {formatCompactNumber(pipeline?.stage1.manifest_artifact_count ?? 0)}
              </p>
            </article>

            <div className="pipeline-arrow" aria-hidden="true">
              <span />
            </div>

            <article className="pipeline-stage card">
              <h3>Stage 2: Snapshot</h3>
              <p className="pipeline-number">{snapshotName}</p>
              <p className="pipeline-meta">
                components {formatCompactNumber(stage2Components)}
              </p>
              <p className="pipeline-meta">{pipeline?.stage2.snapshot_root ?? "--"}</p>
            </article>

            <div className="pipeline-arrow" aria-hidden="true">
              <span />
            </div>

            <article className="pipeline-stage card">
              <h3>Stage 3: Serve</h3>
              <p className="pipeline-number">{pipeline?.serve.status ?? "unknown"}</p>
              <p
                className={`pipeline-meta ${
                  pipeline?.serve.snapshot_mismatch_vs_cache_dir ? "warn" : ""
                }`}
              >
                {pipeline?.serve.snapshot_mismatch_vs_cache_dir
                  ? "snapshot/cache mismatch"
                  : "snapshot/cache aligned"}
              </p>
              <p className="pipeline-meta">{pipeline?.serve.snapshot ?? "--"}</p>
            </article>
          </section>

          <section className="trend-grid">
            <MiniTrendCard
              title="Requests / minute"
              value={`${data.http.requests_per_min.toFixed(1)} rpm`}
              subtitle={`${formatCompactNumber(data.http.total_requests)} requests in window`}
              series={requestSeries}
              color="#f97316"
              formatter={(value) => value.toFixed(1)}
            />
            <MiniTrendCard
              title="P95 latency"
              value={formatMs(data.http.p95_ms)}
              subtitle={`p50 ${formatMs(data.http.p50_ms)}`}
              series={latencySeries}
              color="#58a6ff"
              formatter={(value) => `${value.toFixed(0)} ms`}
            />
            <MiniTrendCard
              title="Server errors"
              value={formatPct(data.http.error_rate_pct)}
              subtitle={`${data.http.server_errors} total 5xx (${formatPct(data.http.success_rate_pct)} success)`}
              series={errorSeries}
              color="#f4b942"
              formatter={(value) => value.toFixed(0)}
            />
          </section>

          <section className="layout-grid">
            <article className="card chart-card chart-card-main">
              <div className="chart-heading">
                <h3>Traffic vs latency</h3>
                <p>{selectedWindowLabel} rolling window</p>
              </div>
              <LatencyChart points={timeline} />
            </article>

            <article className="card chart-card chart-card-side">
              <div className="chart-heading">
                <h3>Load vs latency</h3>
                <p>Risk quadrant highlights saturated behavior</p>
              </div>
              <CorrelationChart points={timeline} />
            </article>

            <BarList
              title="Stage1 assets by type"
              items={assetTypeItems}
              emptyLabel="No stage1 artifacts yet"
            />

            <BarList
              title="Hot routes"
              items={routeItems}
              emptyLabel="No route activity yet"
            />

            <BarList
              title="Demand by component"
              items={demandItems}
              emptyLabel="No component demand yet"
            />

            <BarList
              title="Zero-result components"
              items={zeroResultItems}
              emptyLabel="No zero-result lookups in this window"
            />

            <BarList
              title="Package hits"
              items={packageHitItems}
              emptyLabel="No package traffic yet"
            />

            <BarList
              title="Package returns"
              items={packageReturnItems}
              emptyLabel="No package return events yet"
            />

            <BarList
              title="Component inventory (snapshot)"
              items={componentInventoryItems}
              emptyLabel="No component inventory stats yet"
            />
          </section>
        </>
      ) : null}
    </main>
  );
}
