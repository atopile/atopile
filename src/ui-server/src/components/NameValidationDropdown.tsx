import { AlertCircle, ArrowRight } from 'lucide-react';
import { ValidationResult } from '../utils/nameValidation';

interface NameValidationDropdownProps {
  validation: ValidationResult;
  onApplySuggestion: (suggestion: string) => void;
  className?: string;
}

/**
 * A dropdown that shows name validation errors and suggestions.
 * Only renders when validation.isValid is false.
 */
export function NameValidationDropdown({
  validation,
  onApplySuggestion,
  className = ''
}: NameValidationDropdownProps) {
  if (validation.isValid) {
    return null;
  }

  return (
    <div className={`name-validation-dropdown ${className}`}>
      <div className="validation-error">
        <AlertCircle size={12} className="validation-icon" />
        <span>{validation.error}</span>
      </div>
      {validation.suggestion && (
        <button
          className="validation-suggestion"
          onClick={(e) => {
            e.stopPropagation();
            e.preventDefault();
            onApplySuggestion(validation.suggestion!);
          }}
          type="button"
        >
          <span className="suggestion-label">Use:</span>
          <code className="suggestion-value">{validation.suggestion}</code>
          <ArrowRight size={12} className="suggestion-arrow" />
        </button>
      )}
    </div>
  );
}
