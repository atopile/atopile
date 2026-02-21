import { useEffect, useMemo, useState } from "react";

import type { OriginPoint } from "../types";

interface OriginGlobeProps {
  origins: OriginPoint[];
}

interface ProjectedPoint {
  id: string;
  x: number;
  y: number;
  z: number;
  count: number;
  label: string;
  share: number;
}

function toRadians(value: number): number {
  return (value * Math.PI) / 180;
}

export function OriginGlobe({ origins }: OriginGlobeProps): JSX.Element {
  const [rotationDeg, setRotationDeg] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setRotationDeg((value) => (value + 0.6) % 360);
    }, 32);
    return () => {
      window.clearInterval(timer);
    };
  }, []);

  const projected = useMemo<ProjectedPoint[]>(() => {
    return origins
      .map((origin) => {
        const lat = toRadians(origin.lat);
        const lon = toRadians(origin.lon + rotationDeg);
        const x = Math.cos(lat) * Math.sin(lon);
        const y = Math.sin(lat);
        const z = Math.cos(lat) * Math.cos(lon);
        return {
          id: origin.id,
          x,
          y,
          z,
          count: origin.count,
          label: origin.label,
          share: origin.request_share_pct
        };
      })
      .sort((a, b) => a.z - b.z);
  }, [origins, rotationDeg]);

  return (
    <section className="card globe-card" aria-label="Request origin globe">
      <h3>Request origins</h3>
      {origins.length === 0 ? (
        <div className="empty-state">No origin data in current window</div>
      ) : (
        <div className="globe-layout">
          <svg viewBox="0 0 420 260" className="globe-plot" role="img">
            <defs>
              <radialGradient id="globeFill" cx="35%" cy="35%" r="70%">
                <stop offset="0%" stopColor="rgba(137,180,250,0.35)" />
                <stop offset="55%" stopColor="rgba(137,180,250,0.12)" />
                <stop offset="100%" stopColor="rgba(7,10,35,0.75)" />
              </radialGradient>
            </defs>
            <ellipse cx="210" cy="130" rx="110" ry="110" fill="url(#globeFill)" />
            {[0.2, 0.4, 0.6, 0.8].map((scale) => (
              <ellipse
                key={scale}
                cx="210"
                cy="130"
                rx={110 * scale}
                ry="110"
                className="globe-grid"
              />
            ))}
            {[0.25, 0.5, 0.75].map((scale) => (
              <ellipse
                key={`h-${scale}`}
                cx="210"
                cy="130"
                rx="110"
                ry={110 * scale}
                className="globe-grid"
              />
            ))}

            {projected.map((point) => {
              const cx = 210 + point.x * 110;
              const cy = 130 - point.y * 110;
              const radius = Math.max(2.6, Math.min(10, 1.5 + point.count * 0.35));
              const opacity = point.z > 0 ? 0.95 : 0.25;
              return (
                <g key={point.id} style={{ opacity }}>
                  <circle
                    cx={cx}
                    cy={cy}
                    r={radius}
                    className="origin-dot"
                    aria-hidden="true"
                  />
                  {point.z > 0 ? (
                    <title>{`${point.label}: ${point.share.toFixed(2)}%`}</title>
                  ) : null}
                </g>
              );
            })}
          </svg>
          <ul className="origin-list">
            {origins.slice(0, 6).map((origin) => (
              <li key={origin.id}>
                <span className="origin-name">{origin.label}</span>
                <span className="origin-share">{origin.request_share_pct.toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
