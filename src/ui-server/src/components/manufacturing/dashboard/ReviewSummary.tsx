/**
 * ReviewSummary — Review completion status and comments overview.
 */

import { ClipboardCheck, CheckCircle2, Circle, AlertTriangle } from 'lucide-react';
import { useStore } from '../../../store';
import { REVIEW_PAGES } from './reviewPages';
import type { ReviewPageProps, ReviewPageDefinition } from '../types';

export const ReviewSummaryDefinition: ReviewPageDefinition = {
  id: 'summary',
  label: 'Summary',
  icon: ClipboardCheck,
  order: 60,
  isAvailable: () => true,
};

export function ReviewSummary({ outputs }: ReviewPageProps) {
  const dashboard = useStore((s) => s.manufacturingDashboard);

  if (!dashboard) return null;

  const { reviewedPages, reviewComments } = dashboard;

  const availablePages = REVIEW_PAGES.filter(
    (p) =>
      p.definition.id !== 'summary' &&
      p.definition.id !== 'documents' &&
      (!outputs || p.definition.isAvailable(outputs))
  );

  const allReviewed = availablePages.every((p) => reviewedPages[p.definition.id]);
  const reviewedCount = availablePages.filter((p) => reviewedPages[p.definition.id]).length;

  return (
    <div className="mfg-documents-summary">
      {/* Review status */}
      <div style={{ marginBottom: 24 }}>
        {allReviewed ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--vscode-testing-iconPassed)', fontSize: 14, fontWeight: 600 }}>
            <CheckCircle2 size={18} />
            All items reviewed
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--vscode-editorWarning-foreground)', fontSize: 14 }}>
            <AlertTriangle size={18} />
            {reviewedCount} of {availablePages.length} items reviewed
          </div>
        )}
      </div>

      {/* Review completion table */}
      <table className="mfg-documents-table">
        <thead>
          <tr>
            <th>Item</th>
            <th>Status</th>
            <th>Comment</th>
          </tr>
        </thead>
        <tbody>
          {availablePages.map((page) => {
            const isReviewed = reviewedPages[page.definition.id];
            const comment = reviewComments.find((c) => c.pageId === page.definition.id);
            return (
              <tr key={page.definition.id}>
                <td>{page.definition.label}</td>
                <td>
                  {isReviewed ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--vscode-testing-iconPassed)' }}>
                      <CheckCircle2 size={14} /> Reviewed
                    </span>
                  ) : (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--vscode-descriptionForeground)' }}>
                      <Circle size={14} /> Pending
                    </span>
                  )}
                </td>
                <td className="comment-cell">{comment?.text || '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
