import { useEffect, useState } from 'react';
import type { RequirementData, RequirementsData } from './requirements/types';
import { goToSource } from './requirements/helpers';
import { EditableField } from './requirements/EditableField';
import { GoToSourceIcon } from './requirements/PlotToolbar';
import { useRequirementEditing, RequirementCardBody } from './requirements/RequirementCard';

interface RequirementsDetailPageProps {
  requirementId: string;
  injectedData?: RequirementData | null;
  injectedBuildTime?: string;
}

type WindowGlobals = Window & {
  __ATOPILE_API_URL__?: string;
  __ATOPILE_PROJECT_ROOT__?: string;
  __ATOPILE_TARGET__?: string;
};

export function RequirementsDetailPage({ requirementId, injectedData, injectedBuildTime }: RequirementsDetailPageProps) {
  const [fetchedReq, setFetchedReq] = useState<RequirementData | null>(null);
  const [buildTime, setBuildTime] = useState<string>(injectedBuildTime ?? '');
  const [loading, setLoading] = useState(!injectedData);
  const [error, setError] = useState<string | null>(null);

  // Use injected data or fetched data
  const initialReq = injectedData ?? fetchedReq;
  const editing = useRequirementEditing(initialReq, buildTime);
  const { req, canEdit, hasResult } = editing;
  const plotCount = req?.plotSpecs?.length || 1;

  // Sync build time from injected props
  useEffect(() => {
    if (injectedBuildTime) setBuildTime(injectedBuildTime);
  }, [injectedBuildTime]);

  // Fetch from API if data wasn't injected
  useEffect(() => {
    if (injectedData) return;
    const w = window as WindowGlobals;
    const apiUrl = w.__ATOPILE_API_URL__ || '';
    const projectRoot = w.__ATOPILE_PROJECT_ROOT__ || '';
    const target = w.__ATOPILE_TARGET__ || 'default';
    if (!apiUrl || !projectRoot) { setError('Missing API URL or project root'); setLoading(false); return; }

    const url = `${apiUrl}/api/requirements?project_root=${encodeURIComponent(projectRoot)}&target=${encodeURIComponent(target)}`;
    fetch(url)
      .then(res => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json() as Promise<RequirementsData>; })
      .then(data => { setFetchedReq(data.requirements.find(r => r.id === requirementId) ?? null); setBuildTime(data.buildTime || ''); setLoading(false); })
      .catch(err => { setError(err instanceof Error ? err.message : 'Failed to fetch requirements'); setLoading(false); });
  }, [requirementId, injectedData]);

  if (loading) return <div className="rdp-empty"><div className="rdp-empty-title">Loading requirement...</div></div>;
  if (error) return <div className="rdp-empty"><div className="rdp-empty-title">Error loading requirement</div><div className="rdp-empty-desc">{error}</div></div>;
  if (!req) return <div className="rdp-empty"><div className="rdp-empty-title">Requirement not found</div><div className="rdp-empty-desc">ID: {requirementId || '(none)'}</div></div>;

  return (
    <div className="rdp-root">
      <div className="rall-row">
        <div className="ric-header rall-row-header">
          <div className="ric-name">
            <EditableField value={req.name} className="ric-name-edit" enabled={canEdit} onSave={v => editing.handleFieldChange('req_name', v)} />
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

        <RequirementCardBody
          req={req}
          canEdit={canEdit}
          buildTime={buildTime}
          stale={editing.stale}
          rerunning={editing.rerunning}
          plotCount={plotCount}
          handleFieldChange={editing.handleFieldChange}
          handleRerun={editing.handleRerun}
          handlePlotFieldChange={editing.handlePlotFieldChange}
          handlePlotDirty={editing.handlePlotDirty}
          renderSinglePlot={editing.renderSinglePlot}
          limitVersion={editing.limitVersion}
        />
      </div>
    </div>
  );
}
