/**
 * CommentDialog — modal for viewing and adding review comments.
 */

import { useState, useCallback } from 'react';
import { useStore } from '../../../store';
import { sendActionWithResponse } from '../../../api/websocket';
import type { ReviewComment } from '../types';

interface CommentDialogProps {
  pageId: string;
  pageLabel: string;
  comments: ReviewComment[];
  onClose: () => void;
}

export function CommentDialog({ pageId, pageLabel, comments, onClose }: CommentDialogProps) {
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const addReviewComment = useStore((s) => s.addReviewComment);

  const handleSubmit = useCallback(async () => {
    if (!text.trim() || !dashboard) return;

    setSubmitting(true);
    const res = await sendActionWithResponse('addReviewComment', {
      projectRoot: dashboard.projectRoot,
      target: dashboard.targetName,
      pageId,
      text: text.trim(),
    });

    const r = res?.result as Record<string, unknown> | undefined;
    if (r?.success && r.comment) {
      addReviewComment(r.comment as ReviewComment);
    }
    setText('');
    setSubmitting(false);
  }, [text, dashboard, pageId, addReviewComment]);

  const formatTimestamp = (ts: string) => {
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  };

  return (
    <div className="mfg-comment-dialog" onClick={onClose}>
      <div className="mfg-comment-dialog-inner" onClick={(e) => e.stopPropagation()}>
        <h3>Comments — {pageLabel}</h3>

        {comments.length > 0 && (
          <div className="mfg-comment-list">
            {comments.map((comment, i) => (
              <div key={i} className="mfg-comment-item">
                <div className="mfg-comment-item-meta">
                  {formatTimestamp(comment.timestamp)}
                </div>
                <div>{comment.text}</div>
              </div>
            ))}
          </div>
        )}

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Add a comment..."
          disabled={submitting}
        />

        <div className="mfg-comment-dialog-actions">
          <button className="mfg-btn mfg-btn-secondary" onClick={onClose}>
            Close
          </button>
          <button
            className="mfg-btn mfg-btn-primary"
            onClick={handleSubmit}
            disabled={!text.trim() || submitting}
          >
            {submitting ? 'Saving...' : 'Add Comment'}
          </button>
        </div>
      </div>
    </div>
  );
}
