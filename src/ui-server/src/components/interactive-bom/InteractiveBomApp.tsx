import { useEffect } from 'react';
import { BomSidebar } from './BomSidebar';
import { LayoutViewerWrapper } from './LayoutViewerWrapper';
import { useInteractiveBomStore } from './useInteractiveBomStore';
import { API_URL } from '../../api/config';
import type { BomEnrichment } from './types';
import './interactive-bom.css';

interface BOMComponentAPI {
  mpn?: string;
  manufacturer?: string;
  lcsc?: string;
  type?: string;
  source?: string;
  unitCost?: number;
  stock?: number;
  usages?: { designator?: string }[];
}

export function InteractiveBomApp() {
  const setBomEnrichment = useInteractiveBomStore((s) => s.setBomEnrichment);
  const renderModel = useInteractiveBomStore((s) => s.renderModel);
  const projectRoot = useInteractiveBomStore((s) => s.projectRoot);
  const targetName = useInteractiveBomStore((s) => s.targetName);

  // Fetch BOM enrichment from /api/bom once a PCB is loaded and context is available.
  // Re-fetches when the render model or context changes.
  useEffect(() => {
    if (!renderModel || !projectRoot) return;

    async function fetchBom() {
      try {
        const params = new URLSearchParams();
        params.set('project_root', projectRoot);
        if (targetName) params.set('target', targetName);
        const url = `${API_URL}/api/bom?${params.toString()}`;
        const resp = await fetch(url);
        if (!resp.ok) return;
        const data = (await resp.json()) as { components?: BOMComponentAPI[] };
        if (!data.components) return;

        const enrichment = new Map<string, BomEnrichment>();
        for (const comp of data.components) {
          const info: BomEnrichment = {
            mpn: comp.mpn ?? null,
            manufacturer: comp.manufacturer ?? null,
            lcsc: comp.lcsc ?? null,
            type: comp.type ?? null,
            picked: comp.source === 'picked' ? 'auto' : comp.source ? 'manual' : null,
            unitCost: comp.unitCost ?? null,
            stock: comp.stock ?? null,
          };
          if (comp.usages) {
            for (const usage of comp.usages) {
              if (usage.designator) {
                enrichment.set(usage.designator, info);
              }
            }
          }
        }
        setBomEnrichment(enrichment);
      } catch {
        // BOM API not available — enrichment stays empty
      }
    }
    fetchBom();
  }, [renderModel, projectRoot, targetName, setBomEnrichment]);

  return (
    <div className="ibom-app">
      <BomSidebar />
      <LayoutViewerWrapper />
    </div>
  );
}
