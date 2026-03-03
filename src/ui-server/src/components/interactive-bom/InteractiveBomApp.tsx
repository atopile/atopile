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

  // Attempt to fetch BOM enrichment data
  useEffect(() => {
    async function fetchBom() {
      try {
        const resp = await fetch('/api/bom');
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
  }, [setBomEnrichment]);

  return (
    <div className="ibom-app">
      <BomSidebar />
      <LayoutViewerWrapper />
    </div>
  );
}
