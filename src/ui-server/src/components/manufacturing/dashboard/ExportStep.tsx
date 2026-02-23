/**
 * ExportStep — Documents & Export: combined artifact inventory table with
 * selection checkboxes (left) + quantity & cost (right), configuration below.
 * Unavailable artifacts are grayed out with disabled checkboxes.
 * Artifacts are grouped by categories derived from the backend build targets.
 */

import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  Download,
  FolderOpen,
  ExternalLink,
} from 'lucide-react';
import { useStore } from '../../../store';
import { sendActionWithResponse } from '../../../api/websocket';
import { postMessage, postToExtension } from '../../../api/vscodeApi';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../shared/Table';
import { Checkbox } from '../../shared/Checkbox';
import { Button } from '../../shared/Button';
import { Field, FieldLabel } from '../../shared/Field';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../../shared/Select';
import { Alert } from '../../shared/Alert';
import { Spinner } from '../../shared/Spinner';
import { CATEGORY_CONFIG, FILE_EXPORT_OPTIONS } from '../types';
import type { FileExportType, BuildOutputs, MusterTargetInfo } from '../types';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Category label overrides for the export tab (required → Recommended). */
const EXPORT_CATEGORY_LABEL: Record<string, string> = {
  required: 'Recommended',
};

const OUTPUT_KEY_MAP: Record<FileExportType, keyof BuildOutputs> = {
  gerbers: 'gerbers',
  bom_csv: 'bomCsv',
  bom_json: 'bomJson',
  pick_and_place: 'pickAndPlace',
  step: 'step',
  glb: 'glb',
  kicad_pcb: 'kicadPcb',
  kicad_sch: 'kicadSch',
  svg: 'svg',
  dxf: 'dxf',
  png: 'png',
  testpoints: 'testpoints',
  variables_report: 'variablesReport',
  datasheets: 'datasheets',
};

function getOutputKey(type: FileExportType): string {
  return OUTPUT_KEY_MAP[type] ?? type;
}

function isOutputAvailable(type: FileExportType, outputs: BuildOutputs): boolean {
  const key = OUTPUT_KEY_MAP[type];
  if (!key) return false;
  const val = outputs[key];
  if (Array.isArray(val)) return val.length > 0;
  return !!val;
}

/**
 * Build a FileExportType → category map from backend build targets.
 * Each target's `produces` list tells us which export artifacts it generates,
 * and its `category` tells us which group it belongs to.
 */
function buildCategoryMap(targets: MusterTargetInfo[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (const t of targets) {
    if (!t.category || !t.producesArtifacts) continue;
    for (const a of t.producesArtifacts) {
      map[a.baseName] = t.category;
    }
  }
  return map;
}

interface GroupedOptions {
  category: string;
  label: string;
  options: typeof FILE_EXPORT_OPTIONS;
}

/** Group FILE_EXPORT_OPTIONS by category, sorted by CATEGORY_CONFIG order. */
function getGroupedOptions(categoryMap: Record<string, string>): GroupedOptions[] {
  const grouped: Record<string, typeof FILE_EXPORT_OPTIONS> = {};
  for (const opt of FILE_EXPORT_OPTIONS) {
    const cat = categoryMap[opt.type] ?? 'other';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(opt);
  }
  const sortedCats = Object.keys(grouped).sort((a, b) => {
    const orderA = CATEGORY_CONFIG[a]?.order ?? 99;
    const orderB = CATEGORY_CONFIG[b]?.order ?? 99;
    return orderA - orderB;
  });
  return sortedCats.map((cat) => ({
    category: cat,
    label: EXPORT_CATEGORY_LABEL[cat] ?? CATEGORY_CONFIG[cat]?.label ?? cat,
    options: grouped[cat],
  }));
}

export function ExportStep() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const setDashboardExportConfig = useStore((s) => s.setDashboardExportConfig);
  const setDashboardExporting = useStore((s) => s.setDashboardExporting);
  const setDashboardExportResult = useStore((s) => s.setDashboardExportResult);
  const setDashboardCostEstimate = useStore((s) => s.setDashboardCostEstimate);

  const availableBuildTargets = dashboard?.availableBuildTargets ?? [];

  // Derive artifact → category mapping dynamically from build targets
  const groupedOptions = useMemo(
    () => getGroupedOptions(buildCategoryMap(availableBuildTargets)),
    [availableBuildTargets],
  );

  // Auto-calculate cost when quantities change
  const costTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const projectRoot = dashboard?.projectRoot ?? '';
  const targetName = dashboard?.targetName ?? '';
  const pcbaQuantity = dashboard?.exportConfig.pcbaQuantity ?? 5;

  useEffect(() => {
    if (!dashboard || !projectRoot || !targetName) return;
    if (costTimerRef.current) clearTimeout(costTimerRef.current);
    costTimerRef.current = setTimeout(() => {
      sendActionWithResponse('estimateManufacturingCost', {
        projectRoot,
        targets: [targetName],
        quantity: pcbaQuantity,
      }).then((res) => {
        const r = res?.result as Record<string, unknown> | undefined;
        if (r?.success && r.estimate) {
          setDashboardCostEstimate(r.estimate as typeof dashboard.costEstimate);
        }
      });
    }, 500);
    return () => { if (costTimerRef.current) clearTimeout(costTimerRef.current); };
  }, [projectRoot, targetName, pcbaQuantity]);

  // Auto-select all available file types when outputs first arrive
  const hasAutoSelected = useRef(false);
  useEffect(() => {
    if (!dashboard?.outputs || hasAutoSelected.current) return;
    hasAutoSelected.current = true;
    const available = FILE_EXPORT_OPTIONS
      .filter((opt) => isOutputAvailable(opt.type, dashboard.outputs!))
      .map((opt) => opt.type);
    if (available.length > 0) {
      setDashboardExportConfig({ selectedFileTypes: available });
    }
  }, [dashboard?.outputs, setDashboardExportConfig]);

  if (!dashboard) return null;

  const { exportConfig, outputs, costEstimate, isExporting, exportResult } = dashboard;

  // All available file types (for select-all logic)
  const availableFileTypes = useMemo(() => {
    if (!outputs) return [];
    return FILE_EXPORT_OPTIONS
      .filter((opt) => isOutputAvailable(opt.type, outputs))
      .map((opt) => opt.type);
  }, [outputs]);

  const allSelected = availableFileTypes.length > 0 && availableFileTypes.every((t) => exportConfig.selectedFileTypes.includes(t));

  const handleToggleAll = useCallback(() => {
    if (allSelected) {
      setDashboardExportConfig({ selectedFileTypes: [] });
    } else {
      setDashboardExportConfig({ selectedFileTypes: [...availableFileTypes] });
    }
  }, [allSelected, availableFileTypes, setDashboardExportConfig]);

  const toggleFileType = useCallback((ft: FileExportType) => {
    const types = exportConfig.selectedFileTypes;
    if (types.includes(ft)) {
      setDashboardExportConfig({ selectedFileTypes: types.filter((t) => t !== ft) });
    } else {
      setDashboardExportConfig({ selectedFileTypes: [...types, ft] });
    }
  }, [exportConfig.selectedFileTypes, setDashboardExportConfig]);

  const handleBrowseDirectory = useCallback(() => {
    postMessage({ type: 'browseExportDirectory' });
  }, []);

  const handleExport = useCallback(async () => {
    setDashboardExporting(true);
    const directory = exportConfig.directory || `${projectRoot}/manufacturing`;

    const res = await sendActionWithResponse('exportManufacturingFiles', {
      projectRoot,
      targets: [targetName],
      directory,
      fileTypes: exportConfig.selectedFileTypes,
    });

    const r = res?.result as Record<string, unknown> | undefined;
    setDashboardExportResult({
      success: (r?.success as boolean) ?? false,
      files: (r?.files as string[]) ?? [],
      errors: (r?.errors as string[] | null) ?? null,
    });
  }, [projectRoot, targetName, exportConfig, setDashboardExporting, setDashboardExportResult]);

  const handleOpenFolder = useCallback(() => {
    const dir = exportConfig.directory || `${projectRoot}/manufacturing`;
    postToExtension({ type: 'revealInFinder', path: dir });
  }, [exportConfig.directory, projectRoot]);

  // Helper to render artifact rows for one category group
  const renderArtifactRows = (options: typeof FILE_EXPORT_OPTIONS) =>
    options.map((opt) => {
      const available = outputs ? isOutputAvailable(opt.type, outputs) : false;
      const checked = exportConfig.selectedFileTypes.includes(opt.type);
      const outputKey = getOutputKey(opt.type);
      const fileSize = available && outputs?.fileSizes?.[outputKey]
        ? formatFileSize(outputs.fileSizes[outputKey])
        : null;
      return (
        <TableRow key={opt.type} style={{ opacity: available ? 1 : 0.45 }}>
          <TableCell style={{ width: 32 }}>
            <Checkbox
              checked={checked}
              onCheckedChange={() => toggleFileType(opt.type)}
              disabled={!available}
            />
          </TableCell>
          <TableCell>{opt.label}</TableCell>
          <TableCell className="file-size">{fileSize ?? '—'}</TableCell>
          <TableCell><code style={{ fontSize: 11, opacity: 0.7 }}>{opt.extension}</code></TableCell>
        </TableRow>
      );
    });

  return (
    <div className="mfg-export-step">
      <h2>Documents & Export</h2>
      <p style={{ fontSize: 13, color: 'var(--vscode-descriptionForeground)', margin: '0 0 16px' }}>
        Select the files you want to send to your fabrication house
      </p>

      {/* Two-column layout: artifact table (left) + quantity & cost (right) */}
      <div className="mfg-export-columns">
        {/* Left: artifact inventory table */}
        <div className="mfg-documents-summary" style={{ margin: 0 }}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead style={{ width: 32 }}>
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={handleToggleAll}
                    disabled={availableFileTypes.length === 0}
                    aria-label="Select all"
                  />
                </TableHead>
                <TableHead>Artifact</TableHead>
                <TableHead>File Size</TableHead>
                <TableHead>Type</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {groupedOptions.map((group, gi) => (
                <React.Fragment key={group.category}>
                  <TableRow>
                    <TableCell colSpan={4} style={{ padding: gi === 0 ? '10px 12px 4px' : '14px 12px 4px', fontWeight: 600, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.3px', color: 'var(--vscode-descriptionForeground)', borderBottom: 'none' }}>
                      {group.label}
                    </TableCell>
                  </TableRow>
                  {renderArtifactRows(group.options)}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Right: quantity + cost */}
        <div>
          <div className="mfg-export-section">
            <h3>Quantity</h3>
            <Field className="mfg-export-field">
              <FieldLabel>PCB Quantity</FieldLabel>
              <input
                type="number"
                min={1}
                value={exportConfig.pcbQuantity}
                onChange={(e) => setDashboardExportConfig({ pcbQuantity: Math.max(1, Number(e.target.value)) })}
              />
            </Field>
            <Field className="mfg-export-field">
              <FieldLabel>PCBA Quantity</FieldLabel>
              <input
                type="number"
                min={1}
                value={exportConfig.pcbaQuantity}
                onChange={(e) => setDashboardExportConfig({ pcbaQuantity: Math.max(1, Number(e.target.value)) })}
              />
            </Field>
          </div>

          <div className="mfg-export-section">
            <h3>Cost Estimate</h3>
            {costEstimate ? (
              <div style={{ fontSize: 13 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <span>PCB</span>
                  <span>${costEstimate.pcbCost.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <span>Components</span>
                  <span>${costEstimate.componentsCost.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <span>Assembly</span>
                  <span>${costEstimate.assemblyCost.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontWeight: 600, borderTop: '1px solid var(--vscode-panel-border)', marginTop: 4, paddingTop: 8 }}>
                  <span>Total ({costEstimate.quantity} units)</span>
                  <span>${costEstimate.totalCost.toFixed(2)}</span>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 13, color: 'var(--vscode-descriptionForeground)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Spinner size={14} style={{ opacity: 0.5 }} />
                Calculating...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div style={{ marginTop: 20 }}>
        <div className="mfg-export-section">
          <h3>Configuration</h3>
          <Field className="mfg-export-field">
            <FieldLabel>Output Directory</FieldLabel>
            <div style={{ display: 'flex', gap: 4 }}>
              <input
                type="text"
                value={exportConfig.directory}
                onChange={(e) => setDashboardExportConfig({ directory: e.target.value })}
                placeholder={`${projectRoot}/manufacturing`}
                style={{ flex: 1 }}
              />
              <Button variant="secondary" onClick={handleBrowseDirectory} title="Browse">
                <FolderOpen size={14} />
              </Button>
            </div>
          </Field>

          <Field className="mfg-export-field">
            <FieldLabel>Fab House</FieldLabel>
            <Select
              items={[{ label: 'JLCPCB', value: 'jlcpcb' }]}
              value={exportConfig.fabHouse}
              onValueChange={(v) => setDashboardExportConfig({ fabHouse: v ?? 'jlcpcb' })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="jlcpcb">JLCPCB</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </div>
      </div>

      {/* Export result */}
      {exportResult && (
        <Alert variant={exportResult.success ? 'success' : 'destructive'} style={{ marginTop: 16 }}>
          {exportResult.success
            ? `Exported ${exportResult.files.length} file(s) successfully.`
            : `Export failed: ${exportResult.errors?.join(', ') ?? 'Unknown error'}`}
        </Alert>
      )}

      {/* Actions */}
      <div className="mfg-export-actions">
        <Button
          onClick={handleExport}
          disabled={isExporting || exportConfig.selectedFileTypes.length === 0}
        >
          <Download size={14} /> {isExporting ? 'Exporting...' : 'Export Files'}
        </Button>
        <Button variant="secondary" onClick={handleOpenFolder}>
          <FolderOpen size={14} /> Open Export Folder
        </Button>
        <a
          href="https://cart.jlcpcb.com/quote"
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-secondary btn-md"
          style={{ textDecoration: 'none' }}
        >
          <ExternalLink size={14} /> Go to JLCPCB
        </a>
      </div>
    </div>
  );
}
