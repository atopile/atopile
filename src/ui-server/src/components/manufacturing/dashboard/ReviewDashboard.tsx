/**
 * ManufacturingDashboard — full-screen two-column layout for the
 * Build → Review → Export manufacturing workflow.
 *
 * The top bar shows:
 * - Project/target info
 * - When in review: active page title, reviewed button, comment button
 */

import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Circle, MessageSquare } from 'lucide-react';
import { useStore } from '../../../store';
import { sendActionWithResponse } from '../../../api/websocket';
import { DashboardSidebar } from './DashboardSidebar';
import { DashboardContent } from './DashboardContent';
import { REVIEW_PAGES } from './reviewPages';
import { CommentDialog } from './CommentDialog';
import type { ReviewComment } from '../types';
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
  const setReviewComments = useStore((s) => s.setReviewComments);
  const markReviewed = useStore((s) => s.markReviewed);
  const setDashboardReviewPage = useStore((s) => s.setDashboardReviewPage);
  const setDashboardStep = useStore((s) => s.setDashboardStep);
  const [commentDialogOpen, setCommentDialogOpen] = useState(false);

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

    sendActionWithResponse('getReviewComments', {
      projectRoot: dashboard.projectRoot,
      target: dashboard.targetName,
    }).then((res) => {
      const r = res?.result as Record<string, unknown> | undefined;
      if (r?.success && r.comments) {
        setReviewComments(r.comments as typeof dashboard.reviewComments);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboard?.projectRoot, dashboard?.targetName]);

  // Review-specific header elements (computed before early return so hooks are stable)
  const isReviewStep = dashboard?.activeStep === 'review';
  const activePage = isReviewStep
    ? REVIEW_PAGES.find((p) => p.definition.id === dashboard?.activeReviewPage) ?? null
    : null;
  const isReviewed = activePage ? !!dashboard?.reviewedPages[activePage.definition.id] : false;
  const pageComment = activePage
    ? dashboard?.reviewComments.find((c: ReviewComment) => c.pageId === activePage.definition.id) ?? null
    : null;

  // Advance to the next unreviewed page (or next page if all reviewed)
  const handleMarkReviewed = useCallback(() => {
    if (!activePage || !dashboard) return;
    if (!isReviewed) {
      markReviewed(activePage.definition.id, true);
      const availablePages = REVIEW_PAGES.filter(
        (p) => !dashboard.outputs || p.definition.isAvailable(dashboard.outputs)
      );
      const currentIndex = availablePages.findIndex((p) => p.definition.id === activePage.definition.id);
      // Find next unreviewed page after current
      for (let i = 1; i < availablePages.length; i++) {
        const nextPage = availablePages[(currentIndex + i) % availablePages.length];
        if (!dashboard.reviewedPages[nextPage.definition.id]) {
          setDashboardReviewPage(nextPage.definition.id);
          return;
        }
      }
      // All reviewed — switch to export tab
      setDashboardStep('export');
    } else {
      markReviewed(activePage.definition.id, false);
    }
  }, [activePage, isReviewed, markReviewed, setDashboardReviewPage, setDashboardStep, dashboard]);

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

        {/* Review page title + controls in the top bar */}
        {activePage && (
          <>
            <span className="mfg-header-separator" />
            <span className="mfg-header-page-title">{activePage.definition.label}</span>
            <div className="mfg-header-spacer" />
            <button
              className={`mfg-btn mfg-header-reviewed-btn ${isReviewed ? 'reviewed' : ''}`}
              onClick={handleMarkReviewed}
            >
              {isReviewed ? <CheckCircle2 size={14} /> : <Circle size={14} />}
              {isReviewed ? 'Reviewed' : 'Mark Reviewed'}
            </button>
            <button
              className={`mfg-btn mfg-btn-secondary mfg-header-comment-btn${pageComment ? ' has-comment' : ''}`}
              onClick={() => setCommentDialogOpen(true)}
            >
              <MessageSquare size={14} />
            </button>
          </>
        )}
      </div>
      <div className="mfg-dashboard-body">
        <DashboardSidebar />
        <DashboardContent />
      </div>

      {commentDialogOpen && activePage && (
        <CommentDialog
          pageId={activePage.definition.id}
          pageLabel={activePage.definition.label}
          existingComment={pageComment}
          onClose={() => setCommentDialogOpen(false)}
        />
      )}
    </div>
  );
}
