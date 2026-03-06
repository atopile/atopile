import type { BomGroup, BomEnrichment } from './types';

interface ComponentDetailPanelProps {
  group: BomGroup;
  enrichment: BomEnrichment | null;
}

function DetailField({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="ibom-detail-field">
      <span className="ibom-detail-label">{label}</span>
      <span className="ibom-detail-value">{value || '-'}</span>
    </div>
  );
}

export function ComponentDetailPanel({ group, enrichment }: ComponentDetailPanelProps) {
  return (
    <div className="ibom-detail-panel">
      <div className="ibom-detail-header">
        <span className="ibom-detail-title">Component Details</span>
      </div>
      <div className="ibom-detail-body">
        <DetailField label="Designators" value={group.designators.join(', ')} />
        <DetailField label="Value" value={group.value} />
        <DetailField label="Package" value={group.package} />
        <DetailField label="Footprint" value={group.footprintName} />
        <DetailField label="MPN" value={enrichment?.mpn ?? null} />
        <DetailField label="Manufacturer" value={enrichment?.manufacturer ?? null} />
        <DetailField label="LCSC" value={enrichment?.lcsc ?? null} />
        <DetailField label="Type" value={enrichment?.type ?? null} />
        <DetailField label="Picked" value={enrichment?.picked ?? null} />
        <DetailField label="Unit Cost" value={enrichment?.unitCost != null ? `$${enrichment.unitCost.toFixed(4)}` : null} />
        <DetailField label="Stock" value={enrichment?.stock != null ? enrichment.stock.toLocaleString() : null} />
      </div>
    </div>
  );
}
