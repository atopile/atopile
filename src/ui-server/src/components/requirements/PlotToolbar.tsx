import { useState, useCallback } from 'react';
import type { PlotMeta, RequirementData } from './types';
import { updateRequirement, createPlot } from './api';

interface PlotToolbarProps {
  req: RequirementData;
  specIndex: number;
  onDirty: () => void;
}

const PLOT_FIELDS: { key: string; label: string; placeholder: string }[] = [
  { key: 'title', label: 'Title', placeholder: 'Chart Title' },
  { key: 'x', label: 'X Axis', placeholder: 'time, frequency, or dut.param' },
  { key: 'y', label: 'Y Axis', placeholder: 'dut.net or measurement(net)' },
  { key: 'y_secondary', label: 'Y Secondary', placeholder: 'Optional secondary signal' },
  { key: 'color', label: 'Color by', placeholder: 'dut (for multi-DUT)' },
  { key: 'plot_limits', label: 'Show Limits', placeholder: 'true or false' },
  { key: 'simulation', label: 'Simulation', placeholder: 'Override simulation name' },
];

export function PlotToolbar({ req, specIndex, onDirty }: PlotToolbarProps) {
  const [gearOpen, setGearOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);

  const spec = req.plotSpecs?.[specIndex];
  const meta = spec?.meta;
  const canEdit = !!(req.sourceFile && meta?.varName);

  const handlePlotFieldChange = useCallback(async (field: string, value: string) => {
    if (!req.sourceFile || !meta?.varName) return;
    await updateRequirement({
      source_file: req.sourceFile,
      var_name: meta.varName,
      updates: { [field]: value },
    });
    onDirty();
  }, [req.sourceFile, meta?.varName, onDirty]);

  return (
    <div className="plot-toolbar">
      {/* Editable title overlay */}
      {canEdit && meta?.title && (
        <PlotInlineEdit
          value={meta.title}
          className="plot-title-edit"
          onSave={v => handlePlotFieldChange('title', v)}
        />
      )}

      {/* Icon bar */}
      <div className="plot-toolbar-icons">
        {canEdit && (
          <button
            className="plot-toolbar-btn"
            onClick={() => { setGearOpen(!gearOpen); setAddOpen(false); }}
            title="Plot settings"
          >
            <GearIcon />
          </button>
        )}
        {req.sourceFile && req.varName && (
          <button
            className="plot-toolbar-btn"
            onClick={() => { setAddOpen(!addOpen); setGearOpen(false); }}
            title="Add new plot"
          >
            <PlusIcon />
          </button>
        )}
      </div>

      {/* Gear popover — edit all plot fields */}
      {gearOpen && canEdit && (
        <PlotFieldsPopover
          meta={meta!}
          onFieldChange={handlePlotFieldChange}
          onClose={() => setGearOpen(false)}
        />
      )}

      {/* Add plot popover */}
      {addOpen && req.sourceFile && req.varName && (
        <AddPlotPopover
          req={req}
          onClose={() => setAddOpen(false)}
          onCreated={onDirty}
        />
      )}
    </div>
  );
}

/* ---- Inline text edit (for title overlay) ---- */

function PlotInlineEdit({ value, className, onSave }: {
  value: string;
  className: string;
  onSave: (v: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);

  const commit = async () => {
    if (draft === value) { setEditing(false); return; }
    setSaving(true);
    try { await onSave(draft); } catch { setDraft(value); }
    setSaving(false);
    setEditing(false);
  };

  if (!editing) {
    return (
      <span className={`${className} ric-editable`} onClick={() => setEditing(true)} title="Click to edit">
        {value}
      </span>
    );
  }

  return (
    <input
      className={`${className}-input ric-edit-control ric-edit-input`}
      autoFocus
      value={draft}
      onChange={e => setDraft(e.target.value)}
      onBlur={() => { if (!saving) commit(); }}
      onKeyDown={e => {
        if (e.key === 'Enter') commit();
        if (e.key === 'Escape') { setDraft(value); setEditing(false); }
      }}
      disabled={saving}
      style={{ maxWidth: '250px' }}
    />
  );
}

/* ---- Gear popover — all plot fields ---- */

function PlotFieldsPopover({ meta, onFieldChange, onClose }: {
  meta: PlotMeta;
  onFieldChange: (field: string, value: string) => Promise<void>;
  onClose: () => void;
}) {
  const [saving, setSaving] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>(() => {
    const d: Record<string, string> = {};
    for (const f of PLOT_FIELDS) {
      d[f.key] = (meta as Record<string, string | undefined>)[f.key] ?? '';
    }
    return d;
  });

  const save = async (key: string) => {
    const orig = (meta as Record<string, string | undefined>)[key] ?? '';
    if (drafts[key] === orig) return;
    setSaving(key);
    try { await onFieldChange(key, drafts[key]); } catch { /* */ }
    setSaving(null);
  };

  return (
    <div className="plot-popover" onClick={e => e.stopPropagation()}>
      <div className="plot-popover-header">
        <span>Plot Settings</span>
        <button className="plot-popover-close" onClick={onClose}>&times;</button>
      </div>
      <div className="plot-popover-body">
        {PLOT_FIELDS.map(f => (
          <div className="plot-popover-row" key={f.key}>
            <label className="plot-popover-label">{f.label}</label>
            <input
              className="ric-edit-control ric-edit-input"
              value={drafts[f.key]}
              placeholder={f.placeholder}
              onChange={e => setDrafts(d => ({ ...d, [f.key]: e.target.value }))}
              onBlur={() => save(f.key)}
              onKeyDown={e => { if (e.key === 'Enter') save(f.key); }}
              disabled={saving === f.key}
              style={{ maxWidth: '200px', flex: 1 }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- Add plot popover ---- */

function AddPlotPopover({ req, onClose, onCreated }: {
  req: RequirementData;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [plotName, setPlotName] = useState(`plot_${req.varName || 'new'}`);
  const [title, setTitle] = useState(req.name);
  const [x, setX] = useState('time');
  const [y, setY] = useState(req.net);
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!req.sourceFile || !req.varName) return;
    setCreating(true);
    try {
      await createPlot({
        source_file: req.sourceFile,
        req_var_name: req.varName,
        plot_var_name: plotName,
        fields: { title, x, y },
      });
      onCreated();
      onClose();
    } catch {
      // error
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="plot-popover" onClick={e => e.stopPropagation()}>
      <div className="plot-popover-header">
        <span>Add Plot</span>
        <button className="plot-popover-close" onClick={onClose}>&times;</button>
      </div>
      <div className="plot-popover-body">
        <div className="plot-popover-row">
          <label className="plot-popover-label">Var name</label>
          <input className="ric-edit-control ric-edit-input" value={plotName} onChange={e => setPlotName(e.target.value)} style={{ flex: 1, maxWidth: '200px' }} />
        </div>
        <div className="plot-popover-row">
          <label className="plot-popover-label">Title</label>
          <input className="ric-edit-control ric-edit-input" value={title} onChange={e => setTitle(e.target.value)} style={{ flex: 1, maxWidth: '200px' }} />
        </div>
        <div className="plot-popover-row">
          <label className="plot-popover-label">X axis</label>
          <input className="ric-edit-control ric-edit-input" value={x} onChange={e => setX(e.target.value)} placeholder="time" style={{ flex: 1, maxWidth: '200px' }} />
        </div>
        <div className="plot-popover-row">
          <label className="plot-popover-label">Y axis</label>
          <input className="ric-edit-control ric-edit-input" value={y} onChange={e => setY(e.target.value)} placeholder="dut.net" style={{ flex: 1, maxWidth: '200px' }} />
        </div>
      </div>
      <div className="plot-popover-footer">
        <button className={`ric-rerun-btn ${creating ? 'ric-saving' : ''}`} onClick={handleCreate} disabled={creating}>
          {creating ? 'Creating...' : 'Create Plot'}
        </button>
      </div>
    </div>
  );
}

/* ---- SVG Icons ---- */

function GearIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}
