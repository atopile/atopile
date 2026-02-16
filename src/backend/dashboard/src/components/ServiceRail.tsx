import type { ServiceCard } from "../types";
import { formatMs, formatPct } from "../lib/format";

interface ServiceRailProps {
  services: ServiceCard[];
}

function statusClass(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "online") {
    return "online";
  }
  if (normalized === "degraded" || normalized === "warning") {
    return "degraded";
  }
  return "standby";
}

export function ServiceRail({ services }: ServiceRailProps): JSX.Element {
  return (
    <section className="service-rail" aria-label="Service status">
      {services.map((service) => (
        <article key={service.service} className="service-chip card">
          <header className="service-chip-header">
            <span
              className={`service-dot ${statusClass(service.status)}`}
              aria-hidden="true"
            />
            <div>
              <p className="service-name">{service.service}</p>
              <p className="service-status">{service.status}</p>
            </div>
          </header>
          <dl className="service-chip-metrics">
            <div>
              <dt>RPM</dt>
              <dd>{service.requests_per_min.toFixed(1)}</dd>
            </div>
            <div>
              <dt>P95</dt>
              <dd>{formatMs(service.p95_ms)}</dd>
            </div>
            <div>
              <dt>Error</dt>
              <dd>{formatPct(service.error_rate_pct)}</dd>
            </div>
          </dl>
        </article>
      ))}
    </section>
  );
}
