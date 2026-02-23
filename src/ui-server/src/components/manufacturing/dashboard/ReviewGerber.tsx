/**
 * ReviewGerber — Gerber file viewer using the existing GerberViewer component.
 */

import { Layers } from 'lucide-react';
import GerberViewer from '../../GerberViewer';
import { EmptyState } from '../../shared/EmptyState';
import type { ViewPageProps, ViewPageDefinition } from '../types';
import { API_URL } from '../../../api/config';

export const ReviewGerberDefinition: ViewPageDefinition = {
  id: 'gerber',
  label: 'Gerber Viewer',
  icon: Layers,
  order: 20,
  isAvailable: (outputs) => !!outputs.gerbers,
};

export function ReviewGerber({ outputs }: ViewPageProps) {
  if (!outputs.gerbers) {
    return (
      <EmptyState
        icon={<Layers size={48} />}
        title="No Gerber files available."
        description="Build the project to generate Gerber files."
      />
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
