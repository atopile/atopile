import { useState, useMemo, useEffect } from 'react';
import type { RequirementData, FilterType, SimStatData } from './requirements/types';
import { goToSource, filterRequirements, computeRequirementStats } from './requirements/helpers';
import { EditableField } from './requirements/EditableField';
import { GoToSourceIcon } from './requirements/PlotToolbar';
import { useRequirementEditing, RequirementCardBody } from './requirements/RequirementCard';

interface RequirementsAllPageProps {
  requirements: RequirementData[];
  buildTime: string;
  simStats?: SimStatData[];
  initialSearch?: string;
  buildTarget?: string;
}

const FILTER_LABELS: Record<FilterType, string> = {
  all: 'All',
  pass: 'Pass',
  fail: 'Fail',
  dc: 'DC',
  transient: 'Tran',
  ac: 'AC',
};

/* ------------------------------------------------------------------ */
/*  Single requirement row                                             */
/* ------------------------------------------------------------------ */

function RequirementRow({ req: initialReq, buildTime, layout }: { req: RequirementData; buildTime: string; layout: LayoutMode }) {
  const [collapsed, setCollapsed] = useState(false);
  const editing = useRequirementEditing(initialReq, buildTime);
  const { req, canEdit, hasResult, handleFieldChange } = editing;
  if (!req) return null;
  const plotCount = req.plotSpecs?.length || 1;

  return (
    <div className="rall-row">
      {/* Full-width header */}
      <div className="ric-header rall-row-header">
        <button className="rall-collapse-btn" onClick={() => setCollapsed(c => !c)} title={collapsed ? 'Expand' : 'Collapse'}>
          <svg width="10" height="10" viewBox="0 0 10 10" className={`chevron ${collapsed ? '' : 'open'}`}>
            <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.5" fill="none" />
          </svg>
        </button>
        <div className="ric-name">
          <EditableField value={req.name} className="ric-name-edit" enabled={canEdit} onSave={v => handleFieldChange('req_name', v)} />
        </div>
        {req.sourceFile && req.sourceLine && (
          <button className="ric-goto-btn" onClick={() => goToSource(req.sourceFile, req.sourceLine)} title="Go to requirement definition">
            <GoToSourceIcon />
          </button>
        )}
        <div className={`ric-badge ${hasResult ? (req.passed ? 'pass' : 'fail') : 'pending'}`}>
          {hasResult ? (req.passed ? 'PASS' : 'FAIL') : '---'}
        </div>
      </div>

      {!collapsed && (
        <RequirementCardBody
          req={req}
          canEdit={canEdit}
          buildTime={buildTime}
          stale={editing.stale}
          rerunning={editing.rerunning}
          plotCount={plotCount}
          layout={layout}
          handleFieldChange={editing.handleFieldChange}
          handleRerun={editing.handleRerun}
          handlePlotFieldChange={editing.handlePlotFieldChange}
          handlePlotDirty={editing.handlePlotDirty}
          renderSinglePlot={editing.renderSinglePlot}
          limitVersion={editing.limitVersion}
          collapsed={collapsed}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Simulation timing chart                                            */
/* ------------------------------------------------------------------ */

function SimTimingChart({ stats }: { stats: SimStatData[] }) {
  const [open, setOpen] = useState(false);
  if (!stats.length) return null;

  const totalTime = stats.reduce((sum, s) => sum + s.elapsedS, 0);
  const maxTime = stats[0]?.elapsedS ?? 1;

  return (
    <div className="sim-timing">
      <button className="sim-timing-toggle" onClick={() => setOpen(!open)}>
        <svg width="10" height="10" viewBox="0 0 10 10" className={`chevron ${open ? 'open' : ''}`}>
          <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.5" fill="none" />
        </svg>
        <span>Simulation Timing</span>
        <span className="sim-timing-total">{totalTime.toFixed(1)}s total</span>
        <span className="sim-timing-count">{stats.length} sim{stats.length !== 1 ? 's' : ''}</span>
      </button>
      {open && (
        <div className="sim-timing-body">
          {stats.map((s, i) => {
            const pct = maxTime > 0 ? (s.elapsedS / maxTime) * 100 : 0;
            const pts = s.dataPoints >= 1e6 ? `${(s.dataPoints / 1e6).toFixed(1)}M` : s.dataPoints >= 1000 ? `${(s.dataPoints / 1000).toFixed(1)}k` : String(s.dataPoints);
            return (
              <div className="sim-timing-row" key={i}>
                <span className="sim-timing-name" title={s.name}>{s.name}</span>
                <div className="sim-timing-bar-track">
                  <div className="sim-timing-bar-fill" style={{ width: `${Math.max(pct, 2)}%` }} />
                </div>
                <span className="sim-timing-value">{s.elapsedS.toFixed(1)}s</span>
                <span className="sim-timing-pts">{pts} pts</span>
                <span className="sim-timing-type">{s.simType.replace(/_/g, ' ')}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main all-requirements page                                         */
/* ------------------------------------------------------------------ */

type LayoutMode = 'grid' | 'list';

export function RequirementsAllPage({ requirements, buildTime, simStats, initialSearch, buildTarget }: RequirementsAllPageProps) {
  const [filter, setFilter] = useState<FilterType>('all');
  const [search, setSearch] = useState(initialSearch ?? '');
  const [layout, setLayout] = useState<LayoutMode>('grid');

  // Sync search when initialSearch changes (e.g. clicking a different requirement in sidebar)
  useEffect(() => {
    if (initialSearch !== undefined) {
      setSearch(initialSearch);
    }
  }, [initialSearch]);

  const sorted = useMemo(
    () => [...requirements].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })),
    [requirements],
  );

  const filtered = useMemo(() => filterRequirements(sorted, filter, search), [sorted, filter, search]);

  const { passCount, failCount, pendingCount } = useMemo(() => computeRequirementStats(sorted), [sorted]);

  return (
    <div className="rall-root">
      <div className="rall-header">
        <div className="rall-title">
          {buildTarget || 'All'} Requirements
          <span className="req-sidebar-badge">{sorted.length}</span>
        </div>
        <div className="rall-summary">
          <span className="dot pass" />
          <span>{passCount} passed</span>
          <span className="dot fail" />
          <span>{failCount} failed</span>
          {pendingCount > 0 && (<>
            <span className="dot pending" />
            <span>{pendingCount} pending</span>
          </>)}
        </div>
      </div>

      <div className="rall-toolbar">
        <div className="req-filter-bar" style={{ borderBottom: 'none', padding: 0 }}>
          {(Object.keys(FILTER_LABELS) as FilterType[]).map(f => (
            <button key={f} className={`req-filter-btn ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
              {FILTER_LABELS[f]}
            </button>
          ))}
        </div>
        <div className="rall-search">
          <input className="req-search-input" type="text" placeholder="Search requirements..." value={search} onChange={e => setSearch(e.target.value)} />
          {search && (
            <button className="req-search-clear" onClick={() => setSearch('')} aria-label="Clear search">&times;</button>
          )}
        </div>
        <div className="rall-layout-toggle">
          <button className={`rall-layout-btn${layout === 'grid' ? ' active' : ''}`} onClick={() => setLayout('grid')} title="Grid layout (2 columns)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
            </svg>
          </button>
          <button className={`rall-layout-btn${layout === 'list' ? ' active' : ''}`} onClick={() => setLayout('list')} title="List layout (1 column)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      {simStats && simStats.length > 0 && <SimTimingChart stats={simStats} />}

      <div className="rall-body">
        {filtered.map(req => (
          <RequirementRow key={req.id} req={req} buildTime={buildTime} layout={layout} />
        ))}
        {filtered.length === 0 && (
          <div className="req-empty-state" style={{ padding: '40px' }}>
            <div className="req-empty-state-desc">No requirements match this filter</div>
          </div>
        )}
      </div>
    </div>
  );
}
