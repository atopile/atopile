/**
 * ReviewDocuments — Summary of review completion, comments, and artifact inventory.
 */

import { FileText, CheckCircle2, Circle, AlertTriangle } from 'lucide-react';
import { useStore } from '../../../store';
import { REVIEW_PAGES } from './reviewPages';
import type { ReviewPageProps, ReviewPageDefinition } from '../types';

export const ReviewDocumentsDefinition: ReviewPageDefinition = {
  id: 'documents',
  label: 'Documents',
  icon: FileText,
  order: 50,
  isAvailable: () => true,
};

export function ReviewDocuments({ outputs }: ReviewPageProps) {
  const dashboard = useStore((s) => s.manufacturingDashboard);

  if (!dashboard) return null;

  const { reviewedPages } = dashboard;

  const availablePages = REVIEW_PAGES.filter(
    (p) => p.definition.id !== 'documents' && (!outputs || p.definition.isAvailable(outputs))
  );

  const allReviewed = availablePages.every((p) => reviewedPages[p.definition.id]);
  const reviewedCount = availablePages.filter((p) => reviewedPages[p.definition.id]).length;

  // Aggregate all comments
  const allComments = dashboard.reviewComments;

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
            <th>Comments</th>
          </tr>
        </thead>
        <tbody>
          {availablePages.map((page) => {
            const isReviewed = reviewedPages[page.definition.id];
            const pageComments = allComments.filter((c) => c.pageId === page.definition.id);
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
                <td>{pageComments.length > 0 ? `${pageComments.length} comment(s)` : '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* All comments */}
      {allComments.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>All Comments ({allComments.length})</h3>
          {allComments.map((comment, i) => (
            <div key={i} className="mfg-comment-item">
              <div className="mfg-comment-item-meta">
                {REVIEW_PAGES.find((p) => p.definition.id === comment.pageId)?.definition.label ?? comment.pageId}
                {' — '}
                {new Date(comment.timestamp).toLocaleString()}
              </div>
              <div>{comment.text}</div>
            </div>
          ))}
        </div>
      )}

      {/* Artifact inventory */}
      {outputs && (
        <div style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Artifact Inventory</h3>
          <table className="mfg-documents-table">
            <thead>
              <tr>
                <th>Artifact</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {[
                { label: 'Gerbers', available: !!outputs.gerbers },
                { label: 'BOM (CSV)', available: !!outputs.bomCsv },
                { label: 'BOM (JSON)', available: !!outputs.bomJson },
                { label: 'Pick & Place', available: !!outputs.pickAndPlace },
                { label: '3D Model (GLB)', available: !!outputs.glb },
                { label: '3D Model (STEP)', available: !!outputs.step },
                { label: 'PCB Render (SVG)', available: !!outputs.svg },
                { label: 'KiCad PCB', available: !!outputs.kicadPcb },
              ].map((item) => (
                <tr key={item.label}>
                  <td>{item.label}</td>
                  <td>
                    {item.available ? (
                      <span style={{ color: 'var(--vscode-testing-iconPassed)' }}>Available</span>
                    ) : (
                      <span style={{ color: 'var(--vscode-descriptionForeground)' }}>Not generated</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
