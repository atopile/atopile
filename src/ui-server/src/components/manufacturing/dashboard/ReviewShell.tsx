/**
 * ReviewShell — plugin host for review pages.
 * Bottom action bar has Mark Reviewed + Comment buttons (matching build action bar position).
 */

import { useState } from 'react';
import { CheckCircle2, Circle, MessageSquare } from 'lucide-react';
import { useStore } from '../../../store';
import { REVIEW_PAGES } from './reviewPages';
import { CommentDialog } from './CommentDialog';
import type { BuildOutputs, ReviewComment } from '../types';

export function ReviewShell() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const markReviewed = useStore((s) => s.markReviewed);
  const setDashboardReviewPage = useStore((s) => s.setDashboardReviewPage);
  const setDashboardStep = useStore((s) => s.setDashboardStep);
  const [commentDialogOpen, setCommentDialogOpen] = useState(false);

  if (!dashboard) return null;

  const { activeReviewPage, reviewedPages, outputs, reviewComments, projectRoot, targetName, bomData, boardSummary } = dashboard;

  const activePage = REVIEW_PAGES.find((p) => p.definition.id === activeReviewPage);

  if (!activePage) {
    return (
      <div className="mfg-review-shell">
        <div className="mfg-review-content">
          <div className="mfg-review-placeholder">
            <p>Select a review item from the sidebar.</p>
          </div>
        </div>
      </div>
    );
  }

  const PageComponent = activePage.component;
  const isReviewed = !!reviewedPages[activePage.definition.id];
  const pageComments = reviewComments.filter((c) => c.pageId === activePage.definition.id);
  const pageComment = reviewComments.find((c: ReviewComment) => c.pageId === activePage.definition.id) ?? null;

  const handleMarkReviewed = () => {
    if (!isReviewed) {
      markReviewed(activePage.definition.id, true);
      const availablePages = REVIEW_PAGES.filter(
        (p) => !outputs || p.definition.isAvailable(outputs)
      );
      const currentIndex = availablePages.findIndex((p) => p.definition.id === activePage.definition.id);
      for (let i = 1; i < availablePages.length; i++) {
        const nextPage = availablePages[(currentIndex + i) % availablePages.length];
        if (!reviewedPages[nextPage.definition.id]) {
          setDashboardReviewPage(nextPage.definition.id);
          return;
        }
      }
      setDashboardStep('export');
    } else {
      markReviewed(activePage.definition.id, false);
    }
  };

  return (
    <div className="mfg-review-shell">
      <div className="mfg-review-content">
        <PageComponent
          outputs={outputs ?? {} as BuildOutputs}
          bomData={bomData}
          boardSummary={boardSummary}
          projectRoot={projectRoot}
          targetName={targetName}
          isReviewed={isReviewed}
          onMarkReviewed={(reviewed) => markReviewed(activePage.definition.id, reviewed)}
          comments={pageComments}
          onAddComment={() => {}}
        />
      </div>

      {/* Review actions — pinned to bottom, matching build actions location */}
      <div className="mfg-build-actions">
        <button
          className={`mfg-btn ${isReviewed ? 'mfg-btn-secondary' : 'mfg-btn-primary'}`}
          onClick={handleMarkReviewed}
        >
          {isReviewed ? <CheckCircle2 size={14} /> : <Circle size={14} />}
          {isReviewed ? ' Reviewed' : ' Mark Reviewed'}
        </button>
        <button
          className={`mfg-btn mfg-btn-secondary${pageComment ? ' has-comment' : ''}`}
          onClick={() => setCommentDialogOpen(true)}
        >
          <MessageSquare size={14} /> Comment
        </button>
      </div>

      {commentDialogOpen && (
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
