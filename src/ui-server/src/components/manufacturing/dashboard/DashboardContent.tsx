/**
 * DashboardContent — right column that switches between Build, Review, and Export steps.
 */

import { useStore } from '../../../store';
import { BuildStep } from './BuildStep';
import { ReviewShell } from './ReviewShell';
import { ExportStep } from './ExportStep';

export function DashboardContent() {
  const activeStep = useStore((s) => s.manufacturingDashboard?.activeStep ?? 'build');

  return (
    <div className="mfg-dashboard-content">
      {activeStep === 'build' && <BuildStep />}
      {activeStep === 'review' && <ReviewShell />}
      {activeStep === 'export' && <ExportStep />}
    </div>
  );
}
