/**
 * BuildReviewCard - Per-build card for reviewing build outputs.
 * Shows status, tabs for BOM/3D/Layout, and confirm button.
 */

import { useState, useMemo } from 'react';
import { CheckCircle2, XCircle, Loader2, AlertCircle, Package, Cuboid, Layout } from 'lucide-react';
import type { ManufacturingBuild, BuildOutputs } from './types';
import type { BOMData } from '../../types/build';
import { BOMPanel } from '../BOMPanel';
import ModelViewer from '../ModelViewer';
import KiCanvasEmbed from '../KiCanvasEmbed';

type ReviewTab = 'bom' | '3d' | 'layout';

interface BuildReviewCardProps {
  build: ManufacturingBuild;
  outputs: BuildOutputs | null;
  bomData: BOMData | null;
  isLoadingBom: boolean;
  onConfirm: () => void;
  onRetry: () => void;
}

function StatusIcon({ status }: { status: ManufacturingBuild['status'] }) {
  switch (status) {
    case 'pending':
      return <div className="status-pending-dot" />;
    case 'building':
      return <Loader2 size={16} className="status-spinner" />;
    case 'ready':
      return <AlertCircle size={16} className="status-ready" />;
    case 'confirmed':
      return <CheckCircle2 size={16} className="status-confirmed" />;
    case 'failed':
      return <XCircle size={16} className="status-failed" />;
  }
}

function getStatusLabel(status: ManufacturingBuild['status']): string {
  switch (status) {
    case 'pending':
      return 'Pending';
    case 'building':
      return 'Building...';
    case 'ready':
      return 'Ready for Review';
    case 'confirmed':
      return 'Confirmed';
    case 'failed':
      return 'Build Failed';
  }
}

export function BuildReviewCard({
  build,
  outputs,
  bomData,
  isLoadingBom,
  onConfirm,
  onRetry,
}: BuildReviewCardProps) {
  const [activeTab, setActiveTab] = useState<ReviewTab>('bom');

  const hasOutputs = outputs !== null;
  const canReview = build.status === 'ready' || build.status === 'confirmed';
  const canConfirm = build.status === 'ready';

  // Determine which tabs are available based on outputs
  const availableTabs = useMemo(() => {
    if (!outputs) return [];
    const tabs: ReviewTab[] = [];
    if (outputs.bomJson || outputs.bomCsv) tabs.push('bom');
    if (outputs.glb || outputs.step) tabs.push('3d');
    if (outputs.kicadPcb) tabs.push('layout');
    return tabs;
  }, [outputs]);

  // Ensure active tab is available
  const effectiveTab = availableTabs.includes(activeTab) ? activeTab : availableTabs[0] || 'bom';

  return (
    <div className={`build-review-card status-${build.status}`}>
      <div className="build-review-header">
        <div className="build-review-status">
          <StatusIcon status={build.status} />
          <span className="build-review-status-label">{getStatusLabel(build.status)}</span>
        </div>
        <div className="build-review-name">{build.targetName}</div>
        {build.status === 'failed' && build.error && (
          <button className="build-retry-btn" onClick={onRetry}>
            Retry
          </button>
        )}
        {canConfirm && (
          <button className="build-confirm-btn" onClick={onConfirm}>
            <CheckCircle2 size={14} />
            Confirm
          </button>
        )}
        {build.status === 'confirmed' && (
          <span className="build-confirmed-badge">
            <CheckCircle2 size={12} />
            Confirmed
          </span>
        )}
      </div>

      {build.error && (
        <div className="build-review-error">
          <XCircle size={14} />
          <span>{build.error}</span>
        </div>
      )}

      {canReview && hasOutputs && (
        <>
          <div className="build-review-tabs">
            {availableTabs.includes('bom') && (
              <button
                className={`review-tab ${effectiveTab === 'bom' ? 'active' : ''}`}
                onClick={() => setActiveTab('bom')}
              >
                <Package size={14} />
                BOM
              </button>
            )}
            {availableTabs.includes('3d') && (
              <button
                className={`review-tab ${effectiveTab === '3d' ? 'active' : ''}`}
                onClick={() => setActiveTab('3d')}
              >
                <Cuboid size={14} />
                3D Model
              </button>
            )}
            {availableTabs.includes('layout') && (
              <button
                className={`review-tab ${effectiveTab === 'layout' ? 'active' : ''}`}
                onClick={() => setActiveTab('layout')}
              >
                <Layout size={14} />
                Layout
              </button>
            )}
          </div>

          <div className="build-review-content">
            {effectiveTab === 'bom' && (
              <div className="review-bom-container">
                <BOMPanel
                  bomData={bomData}
                  isLoading={isLoadingBom}
                  isExpanded={true}
                />
              </div>
            )}
            {effectiveTab === '3d' && outputs?.glb && (
              <div className="review-3d-container">
                <ModelViewer
                  src={`/api/file?path=${encodeURIComponent(outputs.glb)}`}
                />
              </div>
            )}
            {effectiveTab === 'layout' && outputs?.kicadPcb && (
              <div className="review-layout-container">
                <KiCanvasEmbed
                  src={`/api/file?path=${encodeURIComponent(outputs.kicadPcb)}`}
                  controls="full"
                  hideReferences={false}
                />
              </div>
            )}
          </div>
        </>
      )}

      {build.status === 'building' && (
        <div className="build-review-building">
          <Loader2 size={24} className="building-spinner" />
          <span>Building {build.targetName}...</span>
        </div>
      )}

      {build.status === 'pending' && (
        <div className="build-review-pending">
          <span>Waiting to build...</span>
        </div>
      )}
    </div>
  );
}
