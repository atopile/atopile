/**
 * Review2DRender — SVG PCB render with zoom/pan.
 */

import { useState, useEffect } from 'react';
import { Image } from 'lucide-react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import type { ReviewPageProps, ReviewPageDefinition } from '../types';
import { API_URL } from '../../../api/config';

export const Review2DRenderDefinition: ReviewPageDefinition = {
  id: '2d-render',
  label: '2D Render',
  icon: Image,
  order: 20,
  isAvailable: (outputs) => !!outputs.svg,
};

export function Review2DRender({ outputs }: ReviewPageProps) {
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!outputs.svg) return;

    fetch(`${API_URL}/api/file?path=${encodeURIComponent(outputs.svg)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then(setSvgContent)
      .catch((e) => setError(e.message));
  }, [outputs.svg]);

  if (!outputs.svg) {
    return (
      <div className="mfg-review-placeholder">
        <Image size={48} />
        <p>No 2D render available.</p>
        <p>Build the project to generate an SVG render.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mfg-review-placeholder">
        <Image size={48} />
        <p>Failed to load SVG: {error}</p>
      </div>
    );
  }

  return (
    <div className="mfg-2d-render">
      <TransformWrapper
        initialScale={1}
        minScale={0.01}
        maxScale={20}
        centerOnInit={true}
        limitToBounds={false}
        doubleClick={{ mode: 'reset' }}
      >
        <TransformComponent wrapperStyle={{ width: '100%', height: '100%' }}>
          {svgContent ? (
            <div dangerouslySetInnerHTML={{ __html: svgContent }} style={{ width: '100%', height: '100%' }} />
          ) : (
            <p style={{ padding: 20, textAlign: 'center' }}>Loading SVG...</p>
          )}
        </TransformComponent>
      </TransformWrapper>
    </div>
  );
}
