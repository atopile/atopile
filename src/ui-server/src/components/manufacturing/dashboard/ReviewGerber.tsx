/**
 * ReviewGerber — Gerber file viewer using the existing GerberViewer component.
 */

import { Layers } from 'lucide-react';
import GerberViewer from '../../GerberViewer';
import type { ReviewPageProps, ReviewPageDefinition } from '../types';
import { API_URL } from '../../../api/config';

export const ReviewGerberDefinition: ReviewPageDefinition = {
  id: 'gerber',
  label: 'Gerber Viewer',
  icon: Layers,
  order: 40,
  isAvailable: (outputs) => !!outputs.gerbers,
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

  return (
    <div className="mfg-gerber-view">
      <GerberViewer
        src={`${API_URL}/api/file?path=${encodeURIComponent(outputs.gerbers)}`}
        hideControls
      />
    </div>
  );
}
