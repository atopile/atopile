/**
 * BuildReviewStep - Step 2 of the manufacturing wizard.
 * Container for BuildReviewCards, handles build pipeline.
 */

import { useMemo, useEffect } from 'react';
import { CheckCircle2 } from 'lucide-react';
import type { ManufacturingBuild, BuildOutputs } from './types';
import type { BOMData } from '../../types/build';
import { BuildReviewCard } from './BuildReviewCard';

interface BuildReviewStepProps {
  builds: ManufacturingBuild[];
  buildOutputs: Record<string, BuildOutputs>;
  bomDataByTarget: Record<string, BOMData | null>;
  isLoadingBomByTarget: Record<string, boolean>;
  onConfirmBuild: (targetName: string) => void;
  onRetryBuild: (targetName: string) => void;
  onStartBuilds: () => void;
  onNext: () => void;
  onBack: () => void;
}

export function BuildReviewStep({
  builds,
  buildOutputs,
  bomDataByTarget,
  isLoadingBomByTarget,
  onConfirmBuild,
  onRetryBuild,
  onStartBuilds,
  onNext,
  onBack,
}: BuildReviewStepProps) {
  // Calculate overall status
  const allConfirmed = useMemo(
    () => builds.length > 0 && builds.every((b) => b.status === 'confirmed'),
    [builds]
  );

  const hasFailedBuilds = useMemo(
    () => builds.some((b) => b.status === 'failed'),
    [builds]
  );

  const hasPendingBuilds = useMemo(
    () => builds.some((b) => b.status === 'pending'),
    [builds]
  );

  const hasBuildingBuilds = useMemo(
    () => builds.some((b) => b.status === 'building'),
    [builds]
  );

  const confirmedCount = useMemo(
    () => builds.filter((b) => b.status === 'confirmed').length,
    [builds]
  );

  // Auto-start builds when step becomes active if there are pending builds
  useEffect(() => {
    if (hasPendingBuilds && !hasBuildingBuilds) {
      onStartBuilds();
    }
  }, [hasPendingBuilds, hasBuildingBuilds, onStartBuilds]);

  const canProceed = allConfirmed;

  return (
    <div className="build-review-step">
      <div className="build-review-header-bar">
        <div className="build-review-progress">
          <span className="progress-text">
            {confirmedCount} of {builds.length} confirmed
          </span>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${(confirmedCount / builds.length) * 100}%` }}
            />
          </div>
        </div>
        {hasFailedBuilds && (
          <div className="build-review-warning">
            Some builds failed. Please retry or remove them to continue.
          </div>
        )}
      </div>

      <div className="build-review-cards">
        {builds.map((build) => (
          <BuildReviewCard
            key={build.targetName}
            build={build}
            outputs={buildOutputs[build.targetName] || null}
            bomData={bomDataByTarget[build.targetName] || null}
            isLoadingBom={isLoadingBomByTarget[build.targetName] || false}
            onConfirm={() => onConfirmBuild(build.targetName)}
            onRetry={() => onRetryBuild(build.targetName)}
          />
        ))}
      </div>

      <div className="step-actions">
        <button className="step-btn secondary" onClick={onBack}>
          Back
        </button>
        <button
          className="step-btn primary"
          onClick={onNext}
          disabled={!canProceed}
        >
          {allConfirmed ? (
            <>
              <CheckCircle2 size={14} />
              Next: Export
            </>
          ) : (
            `Confirm all builds to continue`
          )}
        </button>
      </div>
    </div>
  );
}
