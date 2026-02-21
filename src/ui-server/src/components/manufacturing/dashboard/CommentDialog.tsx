/**
 * CommentDialog — modal for viewing/editing a single review comment per page.
 */

import { useState, useCallback } from 'react';
import { useStore } from '../../../store';
import { sendActionWithResponse } from '../../../api/websocket';
import type { ReviewComment } from '../types';

interface CommentDialogProps {
  pageId: string;
  pageLabel: string;
  existingComment: ReviewComment | null;
  onClose: () => void;
}

export function CommentDialog({ pageId, pageLabel, existingComment, onClose }: CommentDialogProps) {
  const [text, setText] = useState(existingComment?.text ?? '');
  const [submitting, setSubmitting] = useState(false);
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const setReviewComment = useStore((s) => s.setReviewComment);

  const handleSave = useCallback(async () => {
    if (!dashboard) return;

    setSubmitting(true);
    const res = await sendActionWithResponse('addReviewComment', {
      projectRoot: dashboard.projectRoot,
      target: dashboard.targetName,
      pageId,
      text: text.trim(),
    });

    const r = res?.result as Record<string, unknown> | undefined;
    if (r?.success && r.comment) {
      setReviewComment(r.comment as ReviewComment);
    }
    setSubmitting(false);
    onClose();
  }, [text, dashboard, pageId, setReviewComment, onClose]);

  return (
    <div className="mfg-comment-dialog" onClick={onClose}>
      <div className="mfg-comment-dialog-inner" onClick={(e) => e.stopPropagation()}>
        <h3>Comment — {pageLabel}</h3>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Add a comment for this review step..."
          disabled={submitting}
          autoFocus
        />

        <div className="mfg-comment-dialog-actions">
          <button className="mfg-btn mfg-btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="mfg-btn mfg-btn-primary"
            onClick={handleSave}
            disabled={submitting}
          >
            {submitting ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
