/**
 * DashboardContent — right column that switches between Build, View, and Export steps.
 */

import { useStore } from '../../../store';
import { BuildStep } from './BuildStep';
import { ViewerShell } from './ViewerShell';
import { ExportStep } from './ExportStep';

export function DashboardContent() {
  const activeStep = useStore((s) => s.manufacturingDashboard?.activeStep ?? 'build');
  const isViewerStep = activeStep === 'review';

  return (
    <div className={`mfg-dashboard-content${isViewerStep ? ' mfg-dashboard-content--viewer' : ''}`}>
      {activeStep === 'build' && <BuildStep />}
      {activeStep === 'review' && <ViewerShell />}
      {activeStep === 'export' && <ExportStep />}
    </div>
  );
}
