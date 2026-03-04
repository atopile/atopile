import { useEffect } from 'react';
import { BomSidebar } from './BomSidebar';
import { LayoutViewerWrapper } from './LayoutViewerWrapper';
import { useInteractiveBomStore } from './useInteractiveBomStore';
import type { BomEnrichment } from './types';
import './interactive-bom.css';

interface BOMComponentAPI {
  mpn?: string;
  manufacturer?: string;
  lcsc?: string;
  description?: string;
  usages?: { designator?: string }[];
}

export function InteractiveBomApp() {
  const setBomEnrichment = useInteractiveBomStore((s) => s.setBomEnrichment);
  const renderModel = useInteractiveBomStore((s) => s.renderModel);

  // Fetch BOM enrichment from the layout-relative endpoint once a PCB is loaded.
  // Re-fetches when the render model changes (e.g. layout switch).
  useEffect(() => {
    if (!renderModel) return;

    async function fetchBom() {
      try {
        const win = window as any;
        const baseUrl: string = win.__LAYOUT_BASE_URL__ || window.location.origin;
        const apiPrefix: string = win.__LAYOUT_API_PREFIX__ || '/api';

        const projectRoot: string = win.__IBOM_PROJECT_ROOT__ || '';
        const targetName: string = win.__IBOM_TARGET_NAME__ || '';
        const params = new URLSearchParams();
        if (projectRoot) params.set('project_root', projectRoot);
        if (targetName) params.set('target_name', targetName);
        const qs = params.toString();
        const resp = await fetch(`${baseUrl}${apiPrefix}/bom${qs ? `?${qs}` : ''}`);
        if (!resp.ok) return;
        const data = (await resp.json()) as { components?: BOMComponentAPI[] };
        if (!data.components) return;

        const enrichment = new Map<string, BomEnrichment>();
        for (const comp of data.components) {
          const info: BomEnrichment = {
            mpn: comp.mpn ?? null,
            manufacturer: comp.manufacturer ?? null,
            lcsc: comp.lcsc ?? null,
            description: comp.description ?? null,
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
  }, [renderModel, setBomEnrichment]);

  return (
    <div className="ibom-app">
      <BomSidebar />
      <LayoutViewerWrapper />
    </div>
  );
}
