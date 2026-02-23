/**
 * ViewerShell — hosts the active view page (Visual View, Gerber, iBOM).
 */

import { useStore } from '../../../store';
import { VIEW_PAGES } from './viewPages';
import { EmptyState } from '../../shared/EmptyState';
import type { BuildOutputs } from '../types';

export function ViewerShell() {
  const dashboard = useStore((s) => s.manufacturingDashboard);

  if (!dashboard) return null;

  const { activeReviewPage, outputs, projectRoot, targetName, bomData, boardSummary } = dashboard;

  const activePage = VIEW_PAGES.find((p) => p.definition.id === activeReviewPage);

  if (!activePage) {
    return (
      <div className="mfg-review-shell">
        <div className="mfg-review-content">
          <EmptyState title="Select a view from the sidebar." />
        </div>
      </div>
    );
  }

  const PageComponent = activePage.component;

  return (
    <div className="mfg-review-shell">
      <div className="mfg-review-content">
        <PageComponent
          outputs={outputs ?? {} as BuildOutputs}
          bomData={bomData}
          boardSummary={boardSummary}
          projectRoot={projectRoot}
          targetName={targetName}
        />
      </div>
    </div>
  );
}
