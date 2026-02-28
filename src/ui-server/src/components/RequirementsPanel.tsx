import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import type { FilterType } from './requirements/types';
import { RequirementItem } from './requirements/RequirementItem';
import { filterRequirements, computeRequirementStats } from './requirements/helpers';
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

  const requirementsData = useStore((s) => s.requirementsData);
  const isLoading = useStore((s) => s.isLoadingRequirements);
  const selectedProjectRoot = useStore((s) => s.selectedProjectRoot);
  const selectedTargetNames = useStore((s) => s.selectedTargetNames);
  const requirements = useMemo(() =>
    [...(requirementsData?.requirements ?? [])].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })),
    [requirementsData],
  );

  const filteredReqs = useMemo(() => filterRequirements(requirements, filter), [filter, requirements]);

  const { passCount, failCount, pendingCount } = useMemo(() => computeRequirementStats(requirements), [requirements]);

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
    const reqData = requirementsData?.requirements.find(r => r.id === id);
    postMessage({
      type: 'openRequirementDetail',
      requirementId: '__ALL__',
      projectRoot: selectedProjectRoot ?? '',
      target: selectedTargetNames?.[0] ?? 'default',
      requirementData: requirementsData,
      buildTime: requirementsData?.buildTime ?? '',
      initialSearch: reqData?.name ?? '',
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
      initialSearch: '',
    });
  }, [selectedProjectRoot, selectedTargetNames, requirementsData]);

  // When requirements data or target changes, notify the detail webview
  // so it can re-fetch with the current target. The extension silently
  // drops the message if the panel isn't open.
  const prevTarget = useRef(selectedTargetNames?.[0]);
  const prevDataRef = useRef(requirementsData);
  useEffect(() => {
    const target = selectedTargetNames?.[0] ?? 'default';
    const targetChanged = target !== prevTarget.current;
    const dataChanged = requirementsData !== prevDataRef.current;
    prevTarget.current = target;
    prevDataRef.current = requirementsData;

    // Only send if something actually changed (skip initial mount)
    if (!targetChanged && !dataChanged) return;

    postMessage({
      type: 'updateRequirementsPanel',
      target,
      projectRoot: selectedProjectRoot ?? '',
    });
  }, [requirementsData, selectedTargetNames, selectedProjectRoot]);


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
          />
        ))}
        {filteredReqs.length === 0 && (
          <div className="req-empty-state" style={{ padding: '20px' }}>
            <div className="req-empty-state-desc">No requirements match this filter</div>
          </div>
        )}
      </div>

    </div>
  );
}
