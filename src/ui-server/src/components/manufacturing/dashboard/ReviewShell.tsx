/**
 * ReviewShell — plugin host for review pages with shared chrome
 * (Mark as Reviewed toggle + Add Comment button).
 */

import { useState } from 'react';
import { MessageSquare } from 'lucide-react';
import { useStore } from '../../../store';
import { REVIEW_PAGES } from './reviewPages';
import { CommentDialog } from './CommentDialog';
import type { BuildOutputs, ReviewComment } from '../types';

export function ReviewShell() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const markReviewed = useStore((s) => s.markReviewed);
  const [commentDialogOpen, setCommentDialogOpen] = useState(false);

  if (!dashboard) return null;

  const { activeReviewPage, reviewedPages, outputs, reviewComments, projectRoot, targetName, bomData, boardSummary } = dashboard;

  // Find the active page definition + component
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
  const pageComments = reviewComments.filter((c: ReviewComment) => c.pageId === activePage.definition.id);

  return (
    <div className="mfg-review-shell">
      <div className="mfg-review-toolbar">
        <h2>{activePage.definition.label}</h2>
        <label className="mfg-review-toggle">
          <input
            type="checkbox"
            checked={isReviewed}
            onChange={(e) => markReviewed(activePage.definition.id, e.target.checked)}
          />
          Mark as Reviewed
        </label>
        <button
          className="mfg-btn mfg-btn-secondary"
          onClick={() => setCommentDialogOpen(true)}
        >
          <MessageSquare size={14} /> Comment
          {pageComments.length > 0 && ` (${pageComments.length})`}
        </button>
      </div>

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
          onAddComment={() => setCommentDialogOpen(true)}
        />
      </div>

      {commentDialogOpen && (
        <CommentDialog
          pageId={activePage.definition.id}
          pageLabel={activePage.definition.label}
          comments={pageComments}
          onClose={() => setCommentDialogOpen(false)}
        />
      )}
    </div>
  );
}
