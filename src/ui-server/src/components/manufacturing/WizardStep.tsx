/**
 * WizardStep - Accordion-style step wrapper for the manufacturing wizard.
 * Shows as collapsed with summary when not active, expanded when active.
 */

import { ReactNode } from 'react';
import { ChevronDown, Check } from 'lucide-react';

interface WizardStepProps {
  number: 1 | 2 | 3;
  title: string;
  isActive: boolean;
  isComplete: boolean;
  summary?: string;
  onExpand?: () => void;
  children: ReactNode;
  disabled?: boolean;
}

export function WizardStep({
  number,
  title,
  isActive,
  isComplete,
  summary,
  onExpand,
  children,
  disabled = false,
}: WizardStepProps) {
  const handleClick = () => {
    if (!isActive && !disabled && onExpand) {
      onExpand();
    }
  };

  return (
    <div
      className={`wizard-step ${isActive ? 'active' : ''} ${isComplete ? 'complete' : ''} ${disabled ? 'disabled' : ''}`}
    >
      <div
        className={`wizard-step-header ${!isActive && !disabled ? 'clickable' : ''}`}
        onClick={handleClick}
      >
        <div className="wizard-step-number">
          {isComplete ? (
            <Check size={14} className="wizard-step-check" />
          ) : (
            <span>{number}</span>
          )}
        </div>
        <div className="wizard-step-title-area">
          <span className="wizard-step-title">{title}</span>
          {!isActive && summary && (
            <span className="wizard-step-summary">{summary}</span>
          )}
        </div>
        {!isActive && !disabled && (
          <ChevronDown size={16} className="wizard-step-chevron" />
        )}
      </div>
      {isActive && (
        <div className="wizard-step-content">
          {children}
        </div>
      )}
    </div>
  );
}
