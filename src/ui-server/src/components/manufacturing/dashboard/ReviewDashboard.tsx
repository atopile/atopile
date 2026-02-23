/**
 * ManufacturingDashboard — full-screen two-column layout for the
 * Build → View → Export manufacturing workflow.
 *
 * The top bar shows project/target info and (when viewing) the active page title.
 */

import { useEffect } from 'react';
import { useStore } from '../../../store';
import { sendActionWithResponse } from '../../../api/websocket';
import { Separator } from '../../shared/Separator';
import { DashboardSidebar } from './DashboardSidebar';
import { DashboardContent } from './DashboardContent';
import { VIEW_PAGES } from './viewPages';
import './ReviewDashboard.css';

interface ManufacturingDashboardProps {
  projectRoot: string;
  targetName: string;
}

export function ManufacturingDashboard({ projectRoot, targetName }: ManufacturingDashboardProps) {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const openDashboard = useStore((s) => s.openDashboard);
  const setDashboardOutputs = useStore((s) => s.setDashboardOutputs);
  const setDashboardGitStatus = useStore((s) => s.setDashboardGitStatus);

  // Initialize dashboard state on mount
  useEffect(() => {
    if (!projectRoot || !targetName) return;
    openDashboard(projectRoot, targetName);
  }, [projectRoot, targetName, openDashboard]);

  // Fetch initial data once dashboard is open
  useEffect(() => {
    if (!dashboard) return;

    sendActionWithResponse('getManufacturingGitStatus', {
      projectRoot: dashboard.projectRoot,
    }).then((res) => {
      const r = res?.result as Record<string, unknown> | undefined;
      if (r?.success) {
        setDashboardGitStatus({
          hasUncommittedChanges: r.hasUncommittedChanges as boolean,
          changedFiles: (r.changedFiles as string[]) ?? [],
        });
      }
    });

    sendActionWithResponse('getManufacturingOutputs', {
      projectRoot: dashboard.projectRoot,
      target: dashboard.targetName,
    }).then((res) => {
      const r = res?.result as Record<string, unknown> | undefined;
      if (r?.success && r.outputs) {
        setDashboardOutputs(r.outputs as typeof dashboard.outputs);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboard?.projectRoot, dashboard?.targetName]);

  // View-specific header elements
  const isViewStep = dashboard?.activeStep === 'review';
  const activePage = isViewStep
    ? VIEW_PAGES.find((p) => p.definition.id === dashboard?.activeReviewPage) ?? null
    : null;

  if (!dashboard) {
    return (
      <div className="mfg-dashboard">
        <div className="mfg-dashboard-header">
          <span className="mfg-header-target">No project or target specified.</span>
        </div>
        <div className="mfg-dashboard-body">
          <div className="mfg-dashboard-content" />
        </div>
      </div>
    );
  }

  return (
    <div className="mfg-dashboard">
      <div className="mfg-dashboard-header">
        <span className="mfg-header-target">
          {dashboard.projectRoot.split('/').pop()} / {dashboard.targetName}
        </span>

        {/* View page title in the top bar */}
        {activePage && (
          <>
            <Separator orientation="vertical" style={{ height: 18 }} />
            <span className="mfg-header-page-title">{activePage.definition.label}</span>
          </>
        )}
      </div>
      <div className="mfg-dashboard-body">
        <DashboardSidebar />
        <DashboardContent />
      </div>
    </div>
  );
}
