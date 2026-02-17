/**
 * ManufacturingDashboard — full-screen two-column layout for the
 * Build → Review → Export manufacturing workflow.
 */

import { useEffect } from 'react';
import { useStore } from '../../../store';
import { sendActionWithResponse } from '../../../api/websocket';
import { DashboardSidebar } from './DashboardSidebar';
import { DashboardContent } from './DashboardContent';
import './ManufacturingDashboard.css';

interface ManufacturingDashboardProps {
  projectRoot: string;
  targetName: string;
}

export function ManufacturingDashboard({ projectRoot, targetName }: ManufacturingDashboardProps) {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const openDashboard = useStore((s) => s.openDashboard);
  const setDashboardOutputs = useStore((s) => s.setDashboardOutputs);
  const setDashboardGitStatus = useStore((s) => s.setDashboardGitStatus);
  const setReviewComments = useStore((s) => s.setReviewComments);

  // Initialize dashboard state on mount
  useEffect(() => {
    if (!projectRoot || !targetName) return;
    openDashboard(projectRoot, targetName);
  }, [projectRoot, targetName, openDashboard]);

  // Fetch initial data once dashboard is open
  useEffect(() => {
    if (!dashboard) return;

    // Fetch git status
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

    // Fetch existing build outputs
    sendActionWithResponse('getManufacturingOutputs', {
      projectRoot: dashboard.projectRoot,
      target: dashboard.targetName,
    }).then((res) => {
      const r = res?.result as Record<string, unknown> | undefined;
      if (r?.success && r.outputs) {
        setDashboardOutputs(r.outputs as typeof dashboard.outputs);
      }
    });

    // Fetch review comments
    sendActionWithResponse('getReviewComments', {
      projectRoot: dashboard.projectRoot,
      target: dashboard.targetName,
    }).then((res) => {
      const r = res?.result as Record<string, unknown> | undefined;
      if (r?.success && r.comments) {
        setReviewComments(r.comments as typeof dashboard.reviewComments);
      }
    });
    // Only run on initial mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboard?.projectRoot, dashboard?.targetName]);

  if (!dashboard) {
    return (
      <div className="mfg-dashboard">
        <div className="mfg-dashboard-header">
          <h1>Manufacturing Dashboard</h1>
        </div>
        <div className="mfg-dashboard-body">
          <div className="mfg-dashboard-content">
            <p>No project or target specified.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mfg-dashboard">
      <div className="mfg-dashboard-header">
        <h1>Manufacturing Dashboard</h1>
        <span className="mfg-header-target">
          {dashboard.projectRoot.split('/').pop()} / {dashboard.targetName}
        </span>
      </div>
      <div className="mfg-dashboard-body">
        <DashboardSidebar />
        <DashboardContent />
      </div>
    </div>
  );
}
