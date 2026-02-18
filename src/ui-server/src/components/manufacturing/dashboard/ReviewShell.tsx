/**
 * ReviewShell — plugin host for review pages.
 * Toolbar (title, reviewed, comment) has been moved to the top header bar.
 * This shell just renders the active page component.
 */

import { useStore } from '../../../store';
import { REVIEW_PAGES } from './reviewPages';
import type { BuildOutputs } from '../types';

export function ReviewShell() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const markReviewed = useStore((s) => s.markReviewed);

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
    </div>
  );
}
