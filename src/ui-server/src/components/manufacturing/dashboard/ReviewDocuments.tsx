/**
 * ReviewDocuments — Artifact inventory for the build.
 */

import { FileText } from 'lucide-react';
import type { ReviewPageProps, ReviewPageDefinition } from '../types';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const ReviewDocumentsDefinition: ReviewPageDefinition = {
  id: 'documents',
  label: 'Documents',
  icon: FileText,
  order: 50,
  isAvailable: () => true,
};

export function ReviewDocuments({ outputs }: ReviewPageProps) {
  if (!outputs) return null;

  return (
    <div className="mfg-documents-summary">
      <h3 style={{ fontSize: 14, marginBottom: 8 }}>Artifact Inventory</h3>
      <table className="mfg-documents-table">
        <thead>
          <tr>
            <th>Artifact</th>
            <th>Status</th>
            <th>File Size</th>
            <th>Type</th>
          </tr>
        </thead>
        <tbody>
          {[
            { label: 'Gerbers', key: 'gerbers', available: !!outputs.gerbers, ext: '.zip' },
            { label: 'BOM (CSV)', key: 'bomCsv', available: !!outputs.bomCsv, ext: '.csv' },
            { label: 'BOM (JSON)', key: 'bomJson', available: !!outputs.bomJson, ext: '.json' },
            { label: 'Pick & Place', key: 'pickAndPlace', available: !!outputs.pickAndPlace, ext: '.csv' },
            { label: '3D Model (GLB)', key: 'glb', available: !!outputs.glb, ext: '.glb' },
            { label: '3D Model (STEP)', key: 'step', available: !!outputs.step, ext: '.step' },
            { label: 'PCB Render (SVG)', key: 'svg', available: !!outputs.svg, ext: '.svg' },
            { label: 'KiCad PCB', key: 'kicadPcb', available: !!outputs.kicadPcb, ext: '.kicad_pcb' },
          ].map((item) => (
            <tr key={item.label}>
              <td>{item.label}</td>
              <td>
                {item.available ? (
                  <span style={{ color: 'var(--vscode-testing-iconPassed)' }}>Available</span>
                ) : (
                  <span style={{ color: 'var(--vscode-descriptionForeground)' }}>Not generated</span>
                )}
              </td>
              <td className="file-size">
                {item.available && outputs.fileSizes?.[item.key]
                  ? formatFileSize(outputs.fileSizes[item.key])
                  : '—'}
              </td>
              <td><code style={{ fontSize: 11, opacity: 0.7 }}>{item.ext}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
