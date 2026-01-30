/**
 * CostEstimatePanel - Displays cost breakdown for manufacturing.
 * Shows PCB, components, and assembly costs.
 */

import { RefreshCw, Info } from 'lucide-react';
import type { CostEstimate } from './types';

interface CostEstimatePanelProps {
  estimate: CostEstimate | null;
  isLoading: boolean;
  quantity: number;
  onQuantityChange: (quantity: number) => void;
  onRefresh: () => void;
}

function formatCurrency(value: number, currency: string = 'USD'): string {
  if (currency === 'USD') {
    if (value < 1) return `$${value.toFixed(2)}`;
    if (value < 100) return `$${value.toFixed(2)}`;
    return `$${value.toFixed(0)}`;
  }
  return `${value.toFixed(2)} ${currency}`;
}

export function CostEstimatePanel({
  estimate,
  isLoading,
  quantity,
  onQuantityChange,
  onRefresh,
}: CostEstimatePanelProps) {
  if (isLoading) {
    return (
      <div className="cost-estimate-panel loading">
        <RefreshCw size={20} className="loading-spinner" />
        <span>Calculating costs...</span>
      </div>
    );
  }

  if (!estimate) {
    return (
      <div className="cost-estimate-panel empty">
        <span>Cost estimate not available</span>
        <button className="refresh-btn" onClick={onRefresh}>
          <RefreshCw size={14} />
          Calculate
        </button>
      </div>
    );
  }

  const perBoardCost = estimate.totalCost / estimate.quantity;

  return (
    <div className="cost-estimate-panel">
      <div className="cost-estimate-header">
        <span className="cost-title">Cost Estimate</span>
        <div className="cost-quantity">
          <label htmlFor="quantity-input">Quantity:</label>
          <input
            id="quantity-input"
            type="number"
            min={1}
            max={10000}
            value={quantity}
            onChange={(e) => onQuantityChange(parseInt(e.target.value) || 1)}
          />
        </div>
        <button className="refresh-btn" onClick={onRefresh} title="Recalculate">
          <RefreshCw size={14} />
        </button>
      </div>

      <div className="cost-breakdown">
        <div className="cost-row">
          <span className="cost-label">PCB Fabrication</span>
          <span className="cost-value">
            {formatCurrency(estimate.pcbCost, estimate.currency)}
          </span>
        </div>
        {estimate.pcbBreakdown && (
          <div className="cost-sub-breakdown">
            <div className="cost-sub-row">
              <span>Base cost</span>
              <span>{formatCurrency(estimate.pcbBreakdown.baseCost, estimate.currency)}</span>
            </div>
            {estimate.pcbBreakdown.areaCost > 0 && (
              <div className="cost-sub-row">
                <span>Area (per cm²)</span>
                <span>{formatCurrency(estimate.pcbBreakdown.areaCost, estimate.currency)}</span>
              </div>
            )}
            {estimate.pcbBreakdown.layerCost > 0 && (
              <div className="cost-sub-row">
                <span>Extra layers</span>
                <span>{formatCurrency(estimate.pcbBreakdown.layerCost, estimate.currency)}</span>
              </div>
            )}
          </div>
        )}

        <div className="cost-row">
          <span className="cost-label">Components</span>
          <span className="cost-value">
            {formatCurrency(estimate.componentsCost, estimate.currency)}
          </span>
        </div>
        {estimate.componentsBreakdown && (
          <div className="cost-sub-breakdown">
            <div className="cost-sub-row">
              <span>{estimate.componentsBreakdown.uniqueParts} unique parts</span>
              <span>{estimate.componentsBreakdown.totalParts} total</span>
            </div>
          </div>
        )}

        <div className="cost-row">
          <span className="cost-label">Assembly</span>
          <span className="cost-value">
            {formatCurrency(estimate.assemblyCost, estimate.currency)}
          </span>
        </div>
        {estimate.assemblyBreakdown && (
          <div className="cost-sub-breakdown">
            <div className="cost-sub-row">
              <span>Base fee</span>
              <span>{formatCurrency(estimate.assemblyBreakdown.baseCost, estimate.currency)}</span>
            </div>
            <div className="cost-sub-row">
              <span>Per unique part</span>
              <span>{formatCurrency(estimate.assemblyBreakdown.perPartCost, estimate.currency)}</span>
            </div>
          </div>
        )}
      </div>

      <div className="cost-total">
        <div className="cost-total-row">
          <span className="cost-total-label">
            Total ({estimate.quantity} unit{estimate.quantity !== 1 ? 's' : ''})
          </span>
          <span className="cost-total-value">
            {formatCurrency(estimate.totalCost, estimate.currency)}
          </span>
        </div>
        <div className="cost-per-unit">
          <span>{formatCurrency(perBoardCost, estimate.currency)} per board</span>
        </div>
      </div>

      <div className="cost-disclaimer">
        <Info size={12} />
        <span>
          Estimates are approximate (~5x JLCPCB pricing). Actual costs may vary.
        </span>
      </div>
    </div>
  );
}
