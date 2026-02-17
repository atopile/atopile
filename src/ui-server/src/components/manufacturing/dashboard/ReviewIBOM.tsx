/**
 * ReviewIBOM — Interactive BOM placeholder.
 */

import { Table } from 'lucide-react';
import type { ReviewPageProps, ReviewPageDefinition } from '../types';

export const ReviewIBOMDefinition: ReviewPageDefinition = {
  id: 'ibom',
  label: 'Interactive BOM',
  icon: Table,
  order: 30,
  isAvailable: () => true,
};

export function ReviewIBOM({ outputs }: ReviewPageProps) {
  return (
    <div className="mfg-review-placeholder">
      <Table size={48} />
      <p>Interactive BOM viewer</p>
      <span className="coming-soon">Coming Soon</span>
      {outputs.bomCsv && (
        <p style={{ marginTop: 16 }}>
          <a
            href={outputs.bomCsv}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--vscode-textLink-foreground)' }}
          >
            Open BOM CSV
          </a>
        </p>
      )}
    </div>
  );
}
