/**
 * Review3DView — 3D model review page using ModelViewer.
 */

import { Cuboid } from 'lucide-react';
import ModelViewer from '../../ModelViewer';
import type { ReviewPageProps, ReviewPageDefinition } from '../types';
import { API_URL } from '../../../api/config';

export const Review3DViewDefinition: ReviewPageDefinition = {
  id: '3d-view',
  label: '3D View',
  icon: Cuboid,
  order: 10,
  isAvailable: (outputs) => !!outputs.glb,
};

export function Review3DView({ outputs }: ReviewPageProps) {
  if (!outputs.glb) {
    return (
      <div className="mfg-review-placeholder">
        <Cuboid size={48} />
        <p>No 3D model available.</p>
        <p>Build the project to generate a GLB file.</p>
      </div>
    );
  }

  return (
    <div className="mfg-3d-view">
      <ModelViewer
        src={`${API_URL}/api/file?path=${encodeURIComponent(outputs.glb)}`}
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
}
