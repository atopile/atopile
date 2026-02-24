/**
 * DashboardSidebar — left column with Build / View / Export navigation.
 * View items are generated from the VIEW_PAGES registry.
 */

import {
  Hammer,
  Download,
  CheckCircle2,
  Circle,
} from 'lucide-react';
import { useStore } from '../../../store';
import { VIEW_PAGES } from './viewPages';
import type { DashboardStep } from '../types';

export function DashboardSidebar() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const setDashboardStep = useStore((s) => s.setDashboardStep);
  const setDashboardReviewPage = useStore((s) => s.setDashboardReviewPage);

  if (!dashboard) return null;

  const { activeStep, activeReviewPage, outputs } = dashboard;

  const availablePages = VIEW_PAGES.filter(
    (p) => !outputs || p.definition.isAvailable(outputs)
  );

  const handleStepClick = (step: DashboardStep) => {
    setDashboardStep(step);
  };

  const handleViewPageClick = (pageId: string) => {
    setDashboardReviewPage(pageId);
  };

  return (
    <div className="mfg-dashboard-sidebar">
      {/* Build section */}
      <div className="mfg-sidebar-section">
        <h3 className="mfg-sidebar-section-title">Build</h3>
        <button
          className={`mfg-sidebar-item ${activeStep === 'build' ? 'active' : ''}`}
          onClick={() => handleStepClick('build')}
        >
          <span className="mfg-sidebar-item-icon">
            <Hammer size={16} />
          </span>
          <span className="mfg-sidebar-item-label">Build Target</span>
          <span className={`mfg-sidebar-item-status ${dashboard.buildStatus === 'ready' || dashboard.buildStatus === 'confirmed' ? 'complete' : 'pending'}`}>
            {dashboard.buildStatus === 'ready' || dashboard.buildStatus === 'confirmed'
              ? <CheckCircle2 size={14} />
              : <Circle size={14} />}
          </span>
        </button>
      </div>

      {/* View section */}
      <div className="mfg-sidebar-section">
        <h3 className="mfg-sidebar-section-title">View</h3>
        {availablePages.map((page) => {
          const Icon = page.definition.icon;
          const isActive = activeStep === 'review' && activeReviewPage === page.definition.id;

          return (
            <button
              key={page.definition.id}
              className={`mfg-sidebar-item ${isActive ? 'active' : ''}`}
              onClick={() => handleViewPageClick(page.definition.id)}
            >
              <span className="mfg-sidebar-item-icon">
                <Icon size={16} />
              </span>
              <span className="mfg-sidebar-item-label">{page.definition.label}</span>
            </button>
          );
        })}
      </div>

      {/* Export section */}
      <div className="mfg-sidebar-section">
        <h3 className="mfg-sidebar-section-title">Export</h3>
        <button
          className={`mfg-sidebar-item ${activeStep === 'export' ? 'active' : ''}`}
          onClick={() => handleStepClick('export')}
        >
          <span className="mfg-sidebar-item-icon">
            <Download size={16} />
          </span>
          <span className="mfg-sidebar-item-label">Documents & Export</span>
        </button>
      </div>
    </div>
  );
}
