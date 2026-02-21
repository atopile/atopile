/**
 * ExportStep — file selection, configuration, and export actions.
 * Two-column layout: file selection (left) + cost/config (right).
 */

import { useCallback } from 'react';
import {
  Download,
  FolderOpen,
  ExternalLink,
} from 'lucide-react';
import { useStore } from '../../../store';
import { sendActionWithResponse } from '../../../api/websocket';
import { postMessage, postToExtension } from '../../../api/vscodeApi';
import { FILE_EXPORT_OPTIONS } from '../types';
import type { FileExportType, BuildOutputs } from '../types';

export function ExportStep() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const setDashboardExportConfig = useStore((s) => s.setDashboardExportConfig);
  const setDashboardExporting = useStore((s) => s.setDashboardExporting);
  const setDashboardExportResult = useStore((s) => s.setDashboardExportResult);
  const setDashboardCostEstimate = useStore((s) => s.setDashboardCostEstimate);

  if (!dashboard) return null;

  const { projectRoot, targetName, exportConfig, outputs, costEstimate, isExporting, exportResult } = dashboard;

  // Standard file types (those in DEFAULT_FILE_TYPES or the original 8)
  const standardTypes: FileExportType[] = ['gerbers', 'bom_csv', 'bom_json', 'pick_and_place', 'step', 'glb', 'kicad_pcb', 'kicad_sch'];
  const advancedTypes: FileExportType[] = ['svg', 'dxf', 'png', 'testpoints', 'variables_report', 'datasheets'];

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

  const handleEstimateCost = useCallback(async () => {
    const res = await sendActionWithResponse('estimateManufacturingCost', {
      projectRoot,
      targets: [targetName],
      quantity: exportConfig.pcbaQuantity,
    });
    const r = res?.result as Record<string, unknown> | undefined;
    if (r?.success && r.estimate) {
      setDashboardCostEstimate(r.estimate as typeof dashboard.costEstimate);
    }
  }, [projectRoot, targetName, exportConfig.pcbaQuantity, setDashboardCostEstimate]);

  return (
    <div className="mfg-export-step">
      <h2>Export Manufacturing Files</h2>

      <div className="mfg-export-columns">
        {/* Left column: file selection */}
        <div>
          <div className="mfg-export-section">
            <h3>Standard Files</h3>
            {FILE_EXPORT_OPTIONS
              .filter((opt) => standardTypes.includes(opt.type))
              .map((opt) => {
                const available = outputs ? isOutputAvailable(opt.type, outputs) : false;
                return (
                  <label key={opt.type} className="mfg-export-checkbox">
                    <input
                      type="checkbox"
                      checked={exportConfig.selectedFileTypes.includes(opt.type)}
                      onChange={() => toggleFileType(opt.type)}
                      disabled={!available}
                    />
                    <span style={{ opacity: available ? 1 : 0.5 }}>
                      {opt.label}
                      {!available && ' (not available)'}
                    </span>
                  </label>
                );
              })}
          </div>

          <div className="mfg-export-section">
            <h3>Advanced Files</h3>
            {FILE_EXPORT_OPTIONS
              .filter((opt) => advancedTypes.includes(opt.type))
              .map((opt) => {
                const available = outputs ? isOutputAvailable(opt.type, outputs) : false;
                return (
                  <label key={opt.type} className="mfg-export-checkbox">
                    <input
                      type="checkbox"
                      checked={exportConfig.selectedFileTypes.includes(opt.type)}
                      onChange={() => toggleFileType(opt.type)}
                      disabled={!available}
                    />
                    <span style={{ opacity: available ? 1 : 0.5 }}>
                      {opt.label}
                      {!available && ' (not available)'}
                    </span>
                  </label>
                );
              })}
          </div>
        </div>

        {/* Right column: config + cost */}
        <div>
          <div className="mfg-export-section">
            <h3>Configuration</h3>
            <div className="mfg-export-field">
              <label>Output Directory</label>
              <div style={{ display: 'flex', gap: 4 }}>
                <input
                  type="text"
                  value={exportConfig.directory}
                  onChange={(e) => setDashboardExportConfig({ directory: e.target.value })}
                  placeholder={`${projectRoot}/manufacturing`}
                  style={{ flex: 1 }}
                />
                <button className="mfg-btn mfg-btn-secondary" onClick={handleBrowseDirectory} title="Browse">
                  <FolderOpen size={14} />
                </button>
              </div>
            </div>

            <div className="mfg-export-field">
              <label>Fab House</label>
              <select
                value={exportConfig.fabHouse}
                onChange={(e) => setDashboardExportConfig({ fabHouse: e.target.value })}
              >
                <option value="jlcpcb">JLCPCB</option>
              </select>
            </div>

            <div className="mfg-export-field">
              <label>PCB Quantity</label>
              <input
                type="number"
                min={1}
                value={exportConfig.pcbQuantity}
                onChange={(e) => setDashboardExportConfig({ pcbQuantity: Math.max(1, Number(e.target.value)) })}
              />
            </div>

            <div className="mfg-export-field">
              <label>PCBA Quantity</label>
              <input
                type="number"
                min={1}
                value={exportConfig.pcbaQuantity}
                onChange={(e) => setDashboardExportConfig({ pcbaQuantity: Math.max(1, Number(e.target.value)) })}
              />
            </div>
          </div>

          <div className="mfg-export-section">
            <h3>Cost Estimate</h3>
            {!costEstimate ? (
              <button className="mfg-btn mfg-btn-secondary" onClick={handleEstimateCost}>
                Estimate Cost
              </button>
            ) : (
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
                <button className="mfg-btn mfg-btn-secondary" onClick={handleEstimateCost} style={{ marginTop: 8 }}>
                  Recalculate
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Export result */}
      {exportResult && (
        <div style={{ marginTop: 16, padding: '12px 16px', borderRadius: 6, background: exportResult.success ? 'rgba(115, 201, 145, 0.1)' : 'rgba(255, 0, 0, 0.1)', border: `1px solid ${exportResult.success ? 'var(--vscode-testing-iconPassed)' : 'var(--vscode-errorForeground)'}`, fontSize: 13 }}>
          {exportResult.success
            ? `Exported ${exportResult.files.length} file(s) successfully.`
            : `Export failed: ${exportResult.errors?.join(', ') ?? 'Unknown error'}`}
        </div>
      )}

      {/* Actions */}
      <div className="mfg-export-actions">
        <button
          className="mfg-btn mfg-btn-primary"
          onClick={handleExport}
          disabled={isExporting || exportConfig.selectedFileTypes.length === 0}
        >
          <Download size={14} /> {isExporting ? 'Exporting...' : 'Export Files'}
        </button>
        <button className="mfg-btn mfg-btn-secondary" onClick={handleOpenFolder}>
          <FolderOpen size={14} /> Open Export Folder
        </button>
        <a
          href="https://cart.jlcpcb.com/quote"
          target="_blank"
          rel="noopener noreferrer"
          className="mfg-btn mfg-btn-secondary"
          style={{ textDecoration: 'none' }}
        >
          <ExternalLink size={14} /> Go to JLCPCB
        </a>
      </div>
    </div>
  );
}

function isOutputAvailable(type: FileExportType, outputs: BuildOutputs): boolean {
  const map: Record<FileExportType, keyof BuildOutputs> = {
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
  const key = map[type];
  if (!key) return false;
  const val = outputs[key];
  if (Array.isArray(val)) return val.length > 0;
  return !!val;
}
