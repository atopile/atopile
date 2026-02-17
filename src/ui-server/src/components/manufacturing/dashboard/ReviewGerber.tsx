/**
 * ReviewGerber — Gerber file viewer.
 * Falls back to placeholder if gerbers aren't available.
 */

import { Layers } from 'lucide-react';
import type { ReviewPageProps, ReviewPageDefinition } from '../types';

export const ReviewGerberDefinition: ReviewPageDefinition = {
  id: 'gerber',
  label: 'Gerber Viewer',
  icon: Layers,
  order: 40,
  isAvailable: () => true,
};

export function ReviewGerber({ outputs }: ReviewPageProps) {
  if (!outputs.gerbers) {
    return (
      <div className="mfg-review-placeholder">
        <Layers size={48} />
        <p>No Gerber files available.</p>
        <p>Build the project to generate Gerber files.</p>
      </div>
    );
  }

  // The GerberViewer component requires unzipped gerber files.
  // For now, show a placeholder with the gerber zip path.
  return (
    <div className="mfg-review-placeholder">
      <Layers size={48} />
      <p>Gerber files ready for review.</p>
      <span className="coming-soon">Inline viewer coming soon</span>
      <p style={{ marginTop: 16, fontSize: 12, color: 'var(--vscode-descriptionForeground)' }}>
        Gerbers: {outputs.gerbers.split('/').pop()}
      </p>
    </div>
  );
}
