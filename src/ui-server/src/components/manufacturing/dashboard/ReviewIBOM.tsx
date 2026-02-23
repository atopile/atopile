/**
 * ReviewIBOM — Interactive BOM placeholder.
 */

import { Table as TableIcon } from 'lucide-react';
import { EmptyState } from '../../shared/EmptyState';
import { Badge } from '../../shared/Badge';
import type { ViewPageProps, ViewPageDefinition } from '../types';

export const ReviewIBOMDefinition: ViewPageDefinition = {
  id: 'ibom',
  label: 'Interactive BOM',
  icon: TableIcon,
  order: 30,
  isAvailable: () => true,
};

export function ReviewIBOM({ outputs }: ViewPageProps) {
  return (
    <EmptyState
      icon={<TableIcon size={48} />}
      title="Interactive BOM viewer"
    >
      <Badge variant="secondary">Coming Soon</Badge>
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
    </EmptyState>
  );
}
