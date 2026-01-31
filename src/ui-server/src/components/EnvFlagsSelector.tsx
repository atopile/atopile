/**
 * Environment Flags Selector Component
 *
 * Allows users to configure ConfigFlags for test runs.
 * Supports bool, int, float, and string flag types.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import './EnvFlagsSelector.css';

export interface ConfigFlag {
  env_name: string;
  kind: string;
  python_name: string | null;
  default: string | null;
  current: string | null;
  description: string | null;
}

interface EnvFlagsSelectorProps {
  /** Currently configured env vars */
  envVars: Record<string, string>;
  /** Called when env vars change */
  onEnvVarsChange: (envVars: Record<string, string>) => void;
}

// Icons
function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  );
}

function ChevronDown({ className }: { className?: string }) {
  return (
    <svg className={className} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function getFlagType(kind: string): 'bool' | 'int' | 'float' | 'string' | 'enum' {
  switch (kind) {
    case 'ConfigFlag':
      return 'bool';
    case 'ConfigFlagInt':
      return 'int';
    case 'ConfigFlagFloat':
      return 'float';
    case 'ConfigFlagString':
      return 'string';
    case 'ConfigFlagEnum':
      return 'enum';
    default:
      return 'string';
  }
}

function FlagInput({
  flag,
  value,
  onChange,
}: {
  flag: ConfigFlag;
  value: string | undefined;
  onChange: (value: string | undefined) => void;
}) {
  const flagType = getFlagType(flag.kind);
  const isModified = value !== undefined;
  const displayValue = value ?? flag.current ?? flag.default ?? '';

  if (flagType === 'bool') {
    const isChecked = displayValue === '1' || displayValue.toLowerCase() === 'true';
    return (
      <label className="efs-bool-input">
        <input
          type="checkbox"
          checked={isModified ? isChecked : false}
          onChange={(e) => {
            if (e.target.checked) {
              onChange('1');
            } else {
              onChange(undefined);
            }
          }}
        />
        <span className="efs-bool-label">{isModified ? (isChecked ? 'On' : 'Off') : 'Default'}</span>
      </label>
    );
  }

  if (flagType === 'int' || flagType === 'float') {
    const step = flagType === 'float' ? 0.1 : 1;
    const currentNum = parseFloat(displayValue) || 0;

    const increment = () => {
      const newVal = flagType === 'float'
        ? (currentNum + step).toFixed(1)
        : String(Math.round(currentNum + step));
      onChange(newVal);
    };

    const decrement = () => {
      const newVal = flagType === 'float'
        ? (currentNum - step).toFixed(1)
        : String(Math.round(currentNum - step));
      onChange(newVal);
    };

    return (
      <div className="efs-number-wrapper">
        <button type="button" className="efs-number-btn" onClick={decrement}>−</button>
        <input
          type="number"
          className="efs-number-input"
          value={isModified ? displayValue : ''}
          placeholder={flag.default ?? ''}
          step={step}
          onChange={(e) => {
            if (e.target.value === '') {
              onChange(undefined);
            } else {
              onChange(e.target.value);
            }
          }}
        />
        <button type="button" className="efs-number-btn" onClick={increment}>+</button>
      </div>
    );
  }

  // String or enum
  return (
    <input
      type="text"
      className="efs-text-input"
      value={isModified ? displayValue : ''}
      placeholder={flag.default ?? ''}
      onChange={(e) => {
        if (e.target.value === '') {
          onChange(undefined);
        } else {
          onChange(e.target.value);
        }
      }}
    />
  );
}

export function EnvFlagsSelector({ envVars, onEnvVarsChange }: EnvFlagsSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [flags, setFlags] = useState<ConfigFlag[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });

  // Fetch flags on first open
  const loadFlags = useCallback(async () => {
    if (flags.length > 0) return;

    setIsLoading(true);
    setError(null);
    try {
      const response = await api.tests.flags();
      if (response.success) {
        setFlags(response.flags);
      } else {
        setError(response.error || 'Failed to load flags');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load flags');
    } finally {
      setIsLoading(false);
    }
  }, [flags.length]);

  // Load flags and calculate position when dropdown opens
  useEffect(() => {
    if (isOpen) {
      loadFlags();
      // Calculate position based on trigger button
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const dropdownWidth = 380;
        // Position dropdown so its right edge aligns with trigger's right edge
        // But ensure it doesn't go off the left side of the screen
        let left = rect.right - dropdownWidth;
        if (left < 8) {
          left = 8; // Minimum 8px from left edge
        }
        setDropdownPosition({
          top: rect.bottom + 4,
          left,
        });
      }
    }
  }, [isOpen, loadFlags]);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      const clickedInContainer = containerRef.current?.contains(target);
      const clickedInDropdown = dropdownRef.current?.contains(target);
      if (!clickedInContainer && !clickedInDropdown) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleFlagChange = useCallback((envName: string, value: string | undefined) => {
    const newEnvVars = { ...envVars };
    if (value === undefined) {
      delete newEnvVars[envName];
    } else {
      newEnvVars[envName] = value;
    }
    onEnvVarsChange(newEnvVars);
  }, [envVars, onEnvVarsChange]);

  const clearAll = useCallback(() => {
    onEnvVarsChange({});
  }, [onEnvVarsChange]);

  // Filter flags by search term
  const filteredFlags = flags.filter((flag) => {
    if (!filter.trim()) return true;
    const lowerFilter = filter.toLowerCase();
    return (
      flag.env_name.toLowerCase().includes(lowerFilter) ||
      (flag.python_name?.toLowerCase().includes(lowerFilter)) ||
      (flag.description?.toLowerCase().includes(lowerFilter))
    );
  });

  const modifiedCount = Object.keys(envVars).length;

  return (
    <div className="efs-container" ref={containerRef}>
      <button
        className={`efs-trigger ${modifiedCount > 0 ? 'efs-has-mods' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Configure environment flags"
      >
        <SettingsIcon />
        {modifiedCount > 0 && <span className="efs-badge">{modifiedCount}</span>}
        <ChevronDown className={`efs-chevron ${isOpen ? 'rotated' : ''}`} />
      </button>

      {isOpen && (
        <div
          className="efs-dropdown"
          ref={dropdownRef}
          style={{
            position: 'fixed',
            top: dropdownPosition.top,
            left: dropdownPosition.left,
          }}
        >
          <div className="efs-header">
            <span className="efs-title">Environment Flags</span>
            {modifiedCount > 0 && (
              <button className="efs-clear-btn" onClick={clearAll}>
                Clear ({modifiedCount})
              </button>
            )}
          </div>

          <input
            type="text"
            className="efs-filter"
            placeholder="Filter flags..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            autoFocus
          />

          {isLoading && (
            <div className="efs-loading">
              <span className="efs-spinner" />
              Loading flags...
            </div>
          )}

          {error && (
            <div className="efs-error">{error}</div>
          )}

          {!isLoading && !error && (
            <div className="efs-flags-list">
              {filteredFlags.length === 0 ? (
                <div className="efs-empty">
                  {filter ? 'No flags match your filter' : 'No flags found'}
                </div>
              ) : (
                filteredFlags.map((flag) => {
                  const isModified = envVars[flag.env_name] !== undefined;
                  return (
                    <div key={flag.env_name} className={`efs-flag-row ${isModified ? 'modified' : ''}`}>
                      <div className="efs-flag-info">
                        <div className="efs-flag-name">{flag.env_name}</div>
                        {flag.description && (
                          <div className="efs-flag-desc">{flag.description}</div>
                        )}
                        <div className="efs-flag-meta">
                          <span className="efs-flag-type">{getFlagType(flag.kind)}</span>
                          {flag.default && <span className="efs-flag-default">default: {flag.default}</span>}
                        </div>
                      </div>
                      <div className="efs-flag-input">
                        <FlagInput
                          flag={flag}
                          value={envVars[flag.env_name]}
                          onChange={(v) => handleFlagChange(flag.env_name, v)}
                        />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
