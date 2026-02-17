/**
 * DashboardSidebar — left column with Build / Review / Export navigation.
 * Review items are generated from the REVIEW_PAGES registry.
 */

import {
  Hammer,
  Download,
  CheckCircle2,
  Circle,
} from 'lucide-react';
import { useStore } from '../../../store';
import { REVIEW_PAGES } from './reviewPages';
import type { DashboardStep } from '../types';

export function DashboardSidebar() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const setDashboardStep = useStore((s) => s.setDashboardStep);
  const setDashboardReviewPage = useStore((s) => s.setDashboardReviewPage);

  if (!dashboard) return null;

  const { activeStep, activeReviewPage, reviewedPages, outputs } = dashboard;

  const availablePages = REVIEW_PAGES.filter(
    (p) => !outputs || p.definition.isAvailable(outputs)
  );

  const reviewedCount = availablePages.filter(
    (p) => reviewedPages[p.definition.id]
  ).length;

  const handleStepClick = (step: DashboardStep) => {
    setDashboardStep(step);
  };

  const handleReviewPageClick = (pageId: string) => {
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

      {/* Review section */}
      <div className="mfg-sidebar-section">
        <h3 className="mfg-sidebar-section-title">Review</h3>
        {availablePages.map((page) => {
          const Icon = page.definition.icon;
          const isActive = activeStep === 'review' && activeReviewPage === page.definition.id;
          const isReviewed = reviewedPages[page.definition.id];

          return (
            <button
              key={page.definition.id}
              className={`mfg-sidebar-item ${isActive ? 'active' : ''}`}
              onClick={() => handleReviewPageClick(page.definition.id)}
            >
              <span className="mfg-sidebar-item-icon">
                <Icon size={16} />
              </span>
              <span className="mfg-sidebar-item-label">{page.definition.label}</span>
              <span className={`mfg-sidebar-item-status ${isReviewed ? 'complete' : 'pending'}`}>
                {isReviewed ? <CheckCircle2 size={14} /> : <Circle size={14} />}
              </span>
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
          <span className="mfg-sidebar-item-label">Export Files</span>
        </button>
      </div>

      {/* Footer status */}
      <div className="mfg-sidebar-footer">
        {reviewedCount} of {availablePages.length} review items completed
      </div>
    </div>
  );
}
