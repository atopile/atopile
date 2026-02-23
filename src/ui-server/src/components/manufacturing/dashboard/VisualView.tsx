/**
 * VisualView — up to three viewers in a flexible layout:
 *   Left:         Interactive 3D model (GLB)
 *   Right-top:    2D PCB render (SVG)
 *   Right-bottom: 3D board render (PNG)
 *
 * When all three are present the left pane takes ~50 % width and the right
 * column splits vertically.  When any pane is missing the remaining ones
 * expand to fill the space.  Hidden from the sidebar when none are available.
 */

import { Cuboid } from 'lucide-react';
import ModelViewer from '../../ModelViewer';
import type { ViewPageProps, ViewPageDefinition } from '../types';
import { API_URL } from '../../../api/config';

export const VisualViewDefinition: ViewPageDefinition = {
  id: 'visual-view',
  label: 'Visual View',
  icon: Cuboid,
  order: 10,
  isAvailable: (outputs) => !!(outputs.glb || outputs.svg || outputs.png),
};

function fileUrl(path: string) {
  return `${API_URL}/api/file?path=${encodeURIComponent(path)}`;
}

export function VisualView({ outputs }: ViewPageProps) {
  const hasGlb = !!outputs.glb;
  const hasSvg = !!outputs.svg;
  const hasPng = !!outputs.png;
  const hasRight = hasSvg || hasPng;

  const paneCount = [hasGlb, hasSvg, hasPng].filter(Boolean).length;

  // Single pane — fill everything
  if (paneCount === 1) {
    return (
      <div className="mfg-visual-view single">
        {hasGlb && (
          <div className="mfg-visual-view-pane">
            <ModelViewer src={fileUrl(outputs.glb!)} style={{ width: '100%', height: '100%' }} />
          </div>
        )}
        {hasSvg && !hasGlb && (
          <div className="mfg-visual-view-pane">
            <img src={fileUrl(outputs.svg!)} alt="2D PCB render" className="mfg-visual-view-render" />
          </div>
        )}
        {hasPng && !hasGlb && !hasSvg && (
          <div className="mfg-visual-view-pane">
            <img src={fileUrl(outputs.png!)} alt="3D board render" className="mfg-visual-view-render" />
          </div>
        )}
      </div>
    );
  }

  // Two panes — side by side when GLB + one image, stacked when two images
  if (paneCount === 2 && !hasGlb) {
    // Two images, no 3D — stack them vertically in one column
    return (
      <div className="mfg-visual-view stacked">
        {hasSvg && (
          <div className="mfg-visual-view-pane">
            <img src={fileUrl(outputs.svg!)} alt="2D PCB render" className="mfg-visual-view-render" />
          </div>
        )}
        {hasPng && (
          <div className="mfg-visual-view-pane">
            <img src={fileUrl(outputs.png!)} alt="3D board render" className="mfg-visual-view-render" />
          </div>
        )}
      </div>
    );
  }

  // Two or three panes with GLB — GLB left, right column for images
  return (
    <div className="mfg-visual-view columns">
      <div className="mfg-visual-view-pane">
        <ModelViewer src={fileUrl(outputs.glb!)} style={{ width: '100%', height: '100%' }} />
      </div>

      {hasRight && (
        <div className={`mfg-visual-view-right${hasSvg && hasPng ? '' : ' single-child'}`}>
          {hasSvg && (
            <div className="mfg-visual-view-pane">
              <img src={fileUrl(outputs.svg!)} alt="2D PCB render" className="mfg-visual-view-render" />
            </div>
          )}
          {hasPng && (
            <div className="mfg-visual-view-pane">
              <img src={fileUrl(outputs.png!)} alt="3D board render" className="mfg-visual-view-render" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
