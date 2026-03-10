import { useState, useEffect } from 'react';
import { Badge } from '../shared/Badge';
import { StackupCrossSection } from './StackupCrossSection';
import './StackupViewer.css';

interface ManufacturerInfo {
  name?: string | null;
  country?: string | null;
  website?: string | null;
}

export interface StackupLayer {
  index: number;
  layerType: string | null;
  material: string | null;
  thicknessMm: number | null;
  relativePermittivity: number | null;
  lossTangent: number | null;
}

interface StackupData {
  stackupName: string;
  manufacturer: ManufacturerInfo | null;
  layers: StackupLayer[];
  totalThicknessMm: number;
}

function getQueryParams() {
  // Support VS Code webview globals or URL query params (dev mode)
  const win = window as Window & {
    __ATOPILE_STACKUP_PROJECT_ROOT__?: string;
    __ATOPILE_STACKUP_TARGET__?: string;
  };
  const params = new URLSearchParams(window.location.search);
  return {
    projectRoot: win.__ATOPILE_STACKUP_PROJECT_ROOT__ || params.get('project_root') || '',
    target: win.__ATOPILE_STACKUP_TARGET__ || params.get('target') || '',
  };
}

export function StackupViewer() {
  const [data, setData] = useState<StackupData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const { projectRoot, target } = getQueryParams();
    if (!projectRoot || !target) {
      setError('Missing project_root or target query parameters.');
      setLoading(false);
      return;
    }

    const apiBase = (window as Window & { __ATOPILE_API_URL__?: string }).__ATOPILE_API_URL__ || '';
    const url = `${apiBase}/api/stackup?project_root=${encodeURIComponent(projectRoot)}&target=${encodeURIComponent(target)}`;
    fetch(url)
      .then((res) => {
        if (!res.ok) {
          return res.json().then((body) => {
            throw new Error(body.detail || `HTTP ${res.status}`);
          });
        }
        return res.json();
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="stackup-viewer stackup-viewer--loading">
        <span className="stackup-loading-text">Loading stackup...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="stackup-viewer stackup-viewer--error">
        <span className="stackup-error-text">{error}</span>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="stackup-viewer">
      <header className="stackup-header">
        <div className="stackup-header-left">
          <h1 className="stackup-title">{data.stackupName}</h1>
          {data.manufacturer?.name && (
            <Badge variant="info">{data.manufacturer.name}</Badge>
          )}
          {data.manufacturer?.country && (
            <Badge variant="secondary">{data.manufacturer.country}</Badge>
          )}
        </div>
        <div className="stackup-header-right">
          <Badge variant="secondary">
            {data.layers.length} layers
          </Badge>
          <span className="stackup-total-thickness">
            {data.totalThicknessMm.toFixed(2)} mm
          </span>
        </div>
      </header>
      <StackupCrossSection
        layers={data.layers}
        totalThicknessMm={data.totalThicknessMm}
      />
    </div>
  );
}
