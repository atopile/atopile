import { useState, useMemo, useCallback } from 'react';
import type { RequirementData, FilterType } from './requirements/types';
import { RequirementItem } from './requirements/RequirementItem';
import { ReqTooltip } from './requirements/ReqTooltip';
import { postMessage } from '../api/vscodeApi';
import { useStore } from '../store';

interface RequirementsPanelProps {
  isExpanded: boolean;
}

const FILTER_LABELS: Record<FilterType, string> = {
  all: 'All',
  pass: 'Pass',
  fail: 'Fail',
  dc: 'DC',
  transient: 'Tran',
  ac: 'AC',
};

export function RequirementsPanel({ isExpanded }: RequirementsPanelProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>('all');
  const [tooltip, setTooltip] = useState<{ req: RequirementData | null; rect: DOMRect | null }>({
    req: null,
    rect: null,
  });

  const requirementsData = useStore((s) => s.requirementsData);
  const isLoading = useStore((s) => s.isLoadingRequirements);
  const selectedProjectRoot = useStore((s) => s.selectedProjectRoot);
  const selectedTargetNames = useStore((s) => s.selectedTargetNames);
  const requirements = useMemo(() =>
    [...(requirementsData?.requirements ?? [])].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })),
    [requirementsData],
  );

  const hasResult = (r: RequirementData) => r.actual !== null && isFinite(r.actual);

  const filteredReqs = useMemo(() => {
    if (filter === 'all') return requirements;
    if (filter === 'pass') return requirements.filter(r => hasResult(r) && r.passed);
    if (filter === 'fail') return requirements.filter(r => hasResult(r) && !r.passed);
    if (filter === 'dc') return requirements.filter(r => r.capture === 'dcop');
    if (filter === 'transient') return requirements.filter(r => r.capture === 'transient');
    if (filter === 'ac') return requirements.filter(r => r.capture === 'ac');
    return requirements;
  }, [filter, requirements]);

  const passCount = useMemo(() => requirements.filter(r => hasResult(r) && r.passed).length, [requirements]);
  const failCount = useMemo(() => requirements.filter(r => hasResult(r) && !r.passed).length, [requirements]);
  const pendingCount = useMemo(() => requirements.filter(r => !hasResult(r)).length, [requirements]);

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
    const reqData = requirementsData?.requirements.find(r => r.id === id);
    postMessage({
      type: 'openRequirementDetail',
      requirementId: id,
      projectRoot: selectedProjectRoot ?? '',
      target: selectedTargetNames?.[0] ?? 'default',
      requirementData: reqData ?? undefined,
      buildTime: requirementsData?.buildTime ?? '',
    });
  }, [selectedProjectRoot, selectedTargetNames, requirementsData]);

  const handleViewAll = useCallback(() => {
    postMessage({
      type: 'openRequirementDetail',
      requirementId: '__ALL__',
      projectRoot: selectedProjectRoot ?? '',
      target: selectedTargetNames?.[0] ?? 'default',
      requirementData: requirementsData,
      buildTime: requirementsData?.buildTime ?? '',
    });
  }, [selectedProjectRoot, selectedTargetNames, requirementsData]);

  const handleHover = useCallback((req: RequirementData, rect: DOMRect) => {
    setTooltip({ req, rect });
  }, []);

  const handleLeave = useCallback(() => {
    setTooltip({ req: null, rect: null });
  }, []);

  if (!isExpanded) return null;

  if (isLoading) {
    return (
      <div className="req-panel">
        <div className="req-sidebar-header">
          <div className="req-sidebar-title">Requirements</div>
        </div>
        <div className="req-empty-state" style={{ padding: '20px' }}>
          <div className="req-empty-state-desc">Loading requirements...</div>
        </div>
      </div>
    );
  }

  if (requirements.length === 0) {
    return (
      <div className="req-panel">
        <div className="req-sidebar-header">
          <div className="req-sidebar-title">Requirements</div>
        </div>
        <div className="req-empty-state" style={{ padding: '20px' }}>
          <div className="req-empty-state-desc">
            No simulation requirements found. Build a project with requirements to see results here.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="req-panel">
      {/* Header */}
      <div className="req-sidebar-header">
        <div className="req-sidebar-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 11l3 3L22 4" />
            <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
          </svg>
          Requirements
          <span className="req-sidebar-badge">{requirements.length}</span>
        </div>
      </div>

      {/* Summary */}
      <div className="req-summary">
        <div className="req-summary-toggle">
          <span className="dot pass" />
          <span>{passCount} passed</span>
          <span className="dot fail" />
          <span>{failCount} failed</span>
          {pendingCount > 0 && (<>
            <span className="dot pending" />
            <span>{pendingCount} pending</span>
          </>)}
          <button className="req-view-all-btn" onClick={handleViewAll}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            View All
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="req-filter-bar">
        {(Object.keys(FILTER_LABELS) as FilterType[]).map(f => (
          <button
            key={f}
            className={`req-filter-btn ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {FILTER_LABELS[f]}
          </button>
        ))}
      </div>

      {/* Requirement list */}
      <div className="req-list">
        {filteredReqs.map(req => (
          <RequirementItem
            key={req.id}
            req={req}
            selected={selectedId === req.id}
            onClick={() => handleSelect(req.id)}
            onHover={handleHover}
            onLeave={handleLeave}
          />
        ))}
        {filteredReqs.length === 0 && (
          <div className="req-empty-state" style={{ padding: '20px' }}>
            <div className="req-empty-state-desc">No requirements match this filter</div>
          </div>
        )}
      </div>

      <ReqTooltip req={tooltip.req} rect={tooltip.rect} />
    </div>
  );
}
