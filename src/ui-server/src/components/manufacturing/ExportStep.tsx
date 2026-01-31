/**
 * ExportStep - Step 3 of the manufacturing wizard.
 * Directory selection, file type checkboxes, cost estimate, export/purchase buttons.
 */

import { useState } from 'react';
import { FolderOpen, Download, ShoppingCart, Check, AlertCircle } from 'lucide-react';
import { postMessage } from '../../api/vscodeApi';
import type { FileExportType, CostEstimate } from './types';
import { FILE_EXPORT_OPTIONS } from './types';
import { CostEstimatePanel } from './CostEstimatePanel';

interface ExportStepProps {
  selectedFileTypes: FileExportType[];
  exportDirectory: string;
  costEstimate: CostEstimate | null;
  quantity: number;
  isLoadingCost: boolean;
  isExporting: boolean;
  exportError: string | null;
  onToggleFileType: (fileType: FileExportType) => void;
  onDirectoryChange: (directory: string) => void;
  onQuantityChange: (quantity: number) => void;
  onRefreshCost: () => void;
  onExport: () => void;
  onPurchase: () => void;
  onBack: () => void;
}

export function ExportStep({
  selectedFileTypes,
  exportDirectory,
  costEstimate,
  quantity,
  isLoadingCost,
  isExporting,
  exportError,
  onToggleFileType,
  onDirectoryChange,
  onQuantityChange,
  onRefreshCost,
  onExport,
  onPurchase,
  onBack,
}: ExportStepProps) {
  const [directoryInput, setDirectoryInput] = useState(exportDirectory);

  const handleBrowse = () => {
    // Send message to VS Code to open folder picker
    postMessage({ type: 'browseExportDirectory' });
  };

  // Listen for browse result (in real implementation, this would be set up in parent)
  const handleDirectoryInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDirectoryInput(e.target.value);
    onDirectoryChange(e.target.value);
  };

  const canExport = selectedFileTypes.length > 0 && exportDirectory.trim() !== '';

  return (
    <div className="export-step">
      <div className="export-section">
        <h3 className="export-section-title">Output Directory</h3>
        <div className="export-directory-input">
          <input
            type="text"
            value={directoryInput}
            onChange={handleDirectoryInputChange}
            placeholder="Select or enter export directory..."
          />
          <button
            className="browse-btn"
            onClick={handleBrowse}
            title="Browse for directory"
          >
            <FolderOpen size={14} />
            Browse
          </button>
        </div>
      </div>

      <div className="export-section">
        <h3 className="export-section-title">File Types</h3>
        <div className="file-types-grid">
          {FILE_EXPORT_OPTIONS.map((option) => {
            const isSelected = selectedFileTypes.includes(option.type);
            return (
              <div
                key={option.type}
                className={`file-type-option ${isSelected ? 'selected' : ''} ${!option.available ? 'disabled' : ''}`}
                onClick={() => option.available && onToggleFileType(option.type)}
              >
                <div className={`file-type-checkbox ${isSelected ? 'checked' : ''}`}>
                  {isSelected && <Check size={12} />}
                </div>
                <div className="file-type-info">
                  <span className="file-type-label">{option.label}</span>
                  <span className="file-type-description">{option.description}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="export-section">
        <CostEstimatePanel
          estimate={costEstimate}
          isLoading={isLoadingCost}
          quantity={quantity}
          onQuantityChange={onQuantityChange}
          onRefresh={onRefreshCost}
        />
      </div>

      {exportError && (
        <div className="export-error">
          <AlertCircle size={14} />
          <span>{exportError}</span>
        </div>
      )}

      <div className="step-actions export-actions">
        <button className="step-btn secondary" onClick={onBack}>
          Back
        </button>
        <div className="export-buttons">
          <button
            className="step-btn primary"
            onClick={onExport}
            disabled={!canExport || isExporting}
          >
            {isExporting ? (
              <>
                <span className="spinner" />
                Exporting...
              </>
            ) : (
              <>
                <Download size={14} />
                Export Files
              </>
            )}
          </button>
          <button
            className="step-btn purchase"
            onClick={onPurchase}
            disabled={isExporting}
          >
            <ShoppingCart size={14} />
            Purchase
          </button>
        </div>
      </div>
    </div>
  );
}
