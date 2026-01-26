/**
 * SidebarHeader component - Header with logo, version, and settings dropdown.
 */

import { useEffect, useRef, useState } from 'react';
import { Settings, ChevronDown, FolderOpen, Loader2, AlertCircle, Check, GitBranch, Package, Search, X } from 'lucide-react';
import { sendAction } from '../../api/websocket';

// Send action to backend via WebSocket
const action = (name: string, data?: Record<string, unknown>) => {
  if (name === 'openUrl' && data && 'url' in data) {
    const url = (data as { url?: string }).url;
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
      return;
    }
  }
  sendAction(name, data);
};

interface AtopileState {
  isInstalling?: boolean;
  installProgress?: {
    message?: string;
    percent?: number;
  } | null;
  error?: string | null;
  source?: 'release' | 'branch' | 'local';
  currentVersion?: string;
  availableVersions?: string[];
  branch?: string | null;
  availableBranches?: string[];
  localPath?: string | null;
  detectedInstallations?: Array<{
    path: string;
    source: string;
    version?: string | null;
  }>;
}

interface SidebarHeaderProps {
  atopile?: AtopileState;
  developerMode?: boolean;
}

export function SidebarHeader({ atopile, developerMode }: SidebarHeaderProps) {
  const iconUrl =
    typeof window !== 'undefined'
      ? (window as Window & { __ATOPILE_ICON_URL__?: string }).__ATOPILE_ICON_URL__
      : undefined;
  const extensionVersion =
    typeof window !== 'undefined'
      ? (window as Window & { __ATOPILE_EXTENSION_VERSION__?: string })
          .__ATOPILE_EXTENSION_VERSION__
      : undefined;

  // Settings dropdown state
  const [showSettings, setShowSettings] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  // Max concurrent builds setting
  const detectedCores = typeof navigator !== 'undefined' ? navigator.hardwareConcurrency || 4 : 4;
  const [maxConcurrentUseDefault, setMaxConcurrentUseDefault] = useState(true);
  const [maxConcurrentValue, setMaxConcurrentValue] = useState(detectedCores);
  const [defaultMaxConcurrent, setDefaultMaxConcurrent] = useState(detectedCores);

  // Branch search state
  const [branchSearchQuery, setBranchSearchQuery] = useState('');
  const [showBranchDropdown, setShowBranchDropdown] = useState(false);
  const branchDropdownRef = useRef<HTMLDivElement>(null);

  // Local path validation state
  const [localPathValidation, setLocalPathValidation] = useState<{
    isValidating: boolean;
    valid: boolean | null;
    version: string | null;
    error: string | null;
  }>({ isValidating: false, valid: null, version: null, error: null });
  const validateDebounceRef = useRef<NodeJS.Timeout | null>(null);

  // Track pending install (local state for immediate feedback)
  const [pendingInstall, setPendingInstall] = useState<{
    type: 'version' | 'branch' | null;
    value: string | null;
  }>({ type: null, value: null });

  const noReleaseVersions = (atopile?.availableVersions?.length ?? 0) === 0;

  // Clear pending install when the actual version/branch matches what we requested
  // Also timeout after 60 seconds to prevent infinite spinner
  useEffect(() => {
    if (pendingInstall.type === 'version' && atopile?.currentVersion === pendingInstall.value) {
      setPendingInstall({ type: null, value: null });
      return;
    }
    if (pendingInstall.type === 'branch' && atopile?.branch === pendingInstall.value) {
      setPendingInstall({ type: null, value: null });
      return;
    }

    // Timeout after 60 seconds
    if (pendingInstall.type !== null) {
      const timeout = setTimeout(() => {
        setPendingInstall({ type: null, value: null });
      }, 60000);
      return () => clearTimeout(timeout);
    }
  }, [atopile?.currentVersion, atopile?.branch, pendingInstall]);

  // Force user to pick branch/local when no compatible release exists
  useEffect(() => {
    if (noReleaseVersions && atopile?.source === 'release') {
      setPendingInstall({ type: null, value: null });
      action('setAtopileSource', { source: 'branch' });
    }
  }, [noReleaseVersions, atopile?.source]);

  // Helper to check if currently installing (from backend or pending local)
  const isInstalling = atopile?.isInstalling || pendingInstall.type !== null;

  // Close settings dropdown when clicking outside
  useEffect(() => {
    if (!showSettings) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setShowSettings(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showSettings]);

  // Fetch max concurrent setting when settings open
  useEffect(() => {
    if (showSettings) {
      action('getMaxConcurrentSetting');
    }
  }, [showSettings]);

  // Close branch dropdown when clicking outside
  useEffect(() => {
    if (!showBranchDropdown) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (branchDropdownRef.current && !branchDropdownRef.current.contains(e.target as Node)) {
        setShowBranchDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showBranchDropdown]);

  // Validate local path when it changes
  useEffect(() => {
    if (atopile?.source !== 'local' || !atopile?.localPath) {
      setLocalPathValidation({ isValidating: false, valid: null, version: null, error: null });
      return;
    }

    // Debounce validation
    if (validateDebounceRef.current) {
      clearTimeout(validateDebounceRef.current);
    }

    setLocalPathValidation(prev => ({ ...prev, isValidating: true }));

    validateDebounceRef.current = setTimeout(() => {
      action('validateAtopilePath', { path: atopile.localPath });
    }, 500);

    return () => {
      if (validateDebounceRef.current) {
        clearTimeout(validateDebounceRef.current);
      }
    };
  }, [atopile?.source, atopile?.localPath]);

  // Handle action_result events for settings
  useEffect(() => {
    const handleActionResult = (event: Event) => {
      const message = (event as CustomEvent).detail as {
        action?: string;
        result?: {
          success?: boolean;
          // For getMaxConcurrentSetting
          setting?: {
            use_default: boolean;
            custom_value?: number;
            default_value: number;
          };
          // For validateAtopilePath
          valid?: boolean;
          version?: string | null;
          error?: string | null;
        };
      };

      const result = message?.result;

      if (result?.setting) {
        setMaxConcurrentUseDefault(result.setting.use_default);
        setMaxConcurrentValue(result.setting.custom_value || result.setting.default_value);
        setDefaultMaxConcurrent(result.setting.default_value);
      }

      // Handle validateAtopilePath result
      if (message?.action === 'validateAtopilePath' && result) {
        setLocalPathValidation({
          isValidating: false,
          valid: result.valid ?? false,
          version: result.version ?? null,
          error: result.error ?? null,
        });
      }
    };
    window.addEventListener('atopile:action_result', handleActionResult);
    return () => window.removeEventListener('atopile:action_result', handleActionResult);
  }, []);

  return (
    <div className="panel-header">
      <div className="header-title">
        {iconUrl && <img className="header-logo" src={iconUrl} alt="atopile logo" />}
        <span>atopile</span>
        {extensionVersion && <span className="version-badge">v{extensionVersion}</span>}
      </div>
      <div className="header-actions">
        <div className="settings-dropdown-container" ref={settingsRef}>
          <button
            className={`icon-btn${showSettings ? ' active' : ''}`}
            onClick={() => setShowSettings(!showSettings)}
            title="Settings"
          >
            <Settings size={14} />
          </button>
          {showSettings && (
            <div className="settings-dropdown">
              {/* Error Display */}
              {atopile?.error && (
                <div className="settings-error">
                  <AlertCircle size={12} />
                  <span>{atopile.error}</span>
                </div>
              )}
              {noReleaseVersions && (
                <div className="settings-error">
                  <AlertCircle size={12} />
                  <span>No compatible release found. Select a branch or local install.</span>
                </div>
              )}

              {/* Source Type Selector */}
              <div className="settings-group">
                <label className="settings-label">
                  <span className="settings-label-title">Source</span>
                </label>
                <div className="settings-source-buttons">
                  <button
                    className={`source-btn${atopile?.source === 'release' ? ' active' : ''}${noReleaseVersions ? ' disabled' : ''}`}
                    onClick={() => {
                      if (noReleaseVersions) {
                        return;
                      }
                      setPendingInstall({ type: null, value: null });
                      action('setAtopileSource', { source: 'release' });
                    }}
                    title="Use a released version from PyPI"
                    disabled={noReleaseVersions}
                  >
                    <Package size={12} />
                    Release
                  </button>
                  <button
                    className={`source-btn${atopile?.source === 'branch' ? ' active' : ''}`}
                    onClick={() => {
                      setPendingInstall({ type: null, value: null });
                      action('setAtopileSource', { source: 'branch' });
                    }}
                    title="Use a git branch from GitHub"
                  >
                    <GitBranch size={12} />
                    Branch
                  </button>
                  <button
                    className={`source-btn${atopile?.source === 'local' ? ' active' : ''}`}
                    onClick={() => {
                      setPendingInstall({ type: null, value: null });
                      action('setAtopileSource', { source: 'local' });
                    }}
                    title="Use a local installation"
                  >
                    <FolderOpen size={12} />
                    Local
                  </button>
                </div>
              </div>

              {/* Version Selector (when using release) */}
              {atopile?.source === 'release' && !noReleaseVersions && (
                <div className="settings-group">
                  <label className="settings-label">
                    <span className="settings-label-title">Version</span>
                  </label>
                  <div className="settings-select-wrapper">
                    <select
                      className="settings-select"
                      value={atopile?.currentVersion || ''}
                      onChange={(e) => {
                        const newVersion = e.target.value;
                        if (newVersion !== atopile?.currentVersion) {
                          setPendingInstall({ type: 'version', value: newVersion });
                        }
                        action('setAtopileVersion', { version: newVersion });
                      }}
                    >
                      {(atopile?.availableVersions || []).slice(0, 20).map((v) => (
                        <option key={v} value={v}>
                          {v}{v === atopile?.availableVersions?.[0] ? ' (latest)' : ''}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={12} className="select-chevron" />
                  </div>
                  {/* Installation status */}
                  {isInstalling && (
                    <div className="install-status">
                      <Loader2 size={12} className="spinner" />
                      <span>
                        {atopile?.installProgress?.message ||
                         (pendingInstall.type === 'version' ? `Installing v${pendingInstall.value}...` : 'Installing...')}
                      </span>
                      <button
                        className="install-cancel-btn"
                        onClick={() => {
                          setPendingInstall({ type: null, value: null });
                          action('setAtopileInstalling', { installing: false });
                        }}
                        title="Cancel installation"
                      >
                        <X size={10} />
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Branch Selector (when using branch) */}
              {atopile?.source === 'branch' && (
                <div className="settings-group">
                  <label className="settings-label">
                    <span className="settings-label-title">Branch</span>
                  </label>
                  <div className="branch-search-container" ref={branchDropdownRef}>
                    <div className="branch-search-input-wrapper">
                      <Search size={12} className="branch-search-icon" />
                      <input
                        type="text"
                        className="branch-search-input"
                        placeholder="Search branches..."
                        value={branchSearchQuery}
                        onChange={(e) => {
                          setBranchSearchQuery(e.target.value);
                          setShowBranchDropdown(true);
                        }}
                        onFocus={() => setShowBranchDropdown(true)}
                      />
                      {atopile?.branch && !branchSearchQuery && (
                        <span className="branch-current-value">{atopile.branch}</span>
                      )}
                    </div>
                    {showBranchDropdown && (
                      <div className="branch-dropdown">
                        {(atopile?.availableBranches || ['main', 'develop'])
                          .filter(b => !branchSearchQuery || b.toLowerCase().includes(branchSearchQuery.toLowerCase()))
                          .slice(0, 15)
                          .map((b) => (
                            <button
                              key={b}
                              className={`branch-option${b === atopile?.branch ? ' active' : ''}`}
                              onClick={() => {
                                if (b !== atopile?.branch) {
                                  setPendingInstall({ type: 'branch', value: b });
                                }
                                action('setAtopieBranch', { branch: b });
                                setBranchSearchQuery('');
                                setShowBranchDropdown(false);
                              }}
                            >
                              <GitBranch size={12} />
                              <span>{b}</span>
                              {b === 'main' && <span className="branch-tag">default</span>}
                            </button>
                          ))}
                        {branchSearchQuery &&
                          !(atopile?.availableBranches || []).some(b =>
                            b.toLowerCase().includes(branchSearchQuery.toLowerCase())
                          ) && (
                          <div className="branch-no-results">No branches match "{branchSearchQuery}"</div>
                        )}
                      </div>
                    )}
                  </div>
                  <span className="settings-hint">
                    Installs from git+https://github.com/atopile/atopile.git@{atopile?.branch || 'main'}
                  </span>
                  {/* Installation status */}
                  {isInstalling && (
                    <div className="install-status">
                      <Loader2 size={12} className="spinner" />
                      <span>
                        {atopile?.installProgress?.message ||
                         (pendingInstall.type === 'branch' ? `Installing ${pendingInstall.value}...` : 'Installing...')}
                      </span>
                      <button
                        className="install-cancel-btn"
                        onClick={() => {
                          setPendingInstall({ type: null, value: null });
                          action('setAtopileInstalling', { installing: false });
                        }}
                        title="Cancel installation"
                      >
                        <X size={10} />
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Local Path Input (when using local) */}
              {atopile?.source === 'local' && (
                <div className="settings-group local-path-section">
                  <label className="settings-label">
                    <span className="settings-label-title">Local Path</span>
                  </label>

                  {/* Detected installations */}
                  {(atopile?.detectedInstallations?.length ?? 0) > 0 && (
                    <div className="detected-installations">
                      <span className="detected-label">Detected:</span>
                      {atopile?.detectedInstallations?.map((inst, i) => (
                        <button
                          key={i}
                          className={`detected-item${atopile?.localPath === inst.path ? ' active' : ''}`}
                          onClick={() => action('setAtopileLocalPath', { path: inst.path })}
                          title={inst.path}
                        >
                          <span className="detected-source">{inst.source}</span>
                          {inst.version && <span className="detected-version">v{inst.version}</span>}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Manual path input */}
                  <div className="settings-path-input">
                    <input
                      type="text"
                      className={`settings-input${localPathValidation.valid === true ? ' valid' : ''}${localPathValidation.valid === false ? ' invalid' : ''}`}
                      placeholder="/path/to/atopile or ato"
                      value={atopile?.localPath || ''}
                      onChange={(e) => {
                        action('setAtopileLocalPath', { path: e.target.value });
                      }}
                    />
                    <button
                      className="path-browse-btn"
                      onClick={() => action('browseAtopilePath')}
                      title="Browse..."
                    >
                      <FolderOpen size={12} />
                    </button>
                  </div>

                  {/* Validation status */}
                  {atopile?.localPath && (
                    <div className={`path-validation-status${localPathValidation.valid === true ? ' valid' : ''}${localPathValidation.valid === false ? ' invalid' : ''}`}>
                      {localPathValidation.isValidating ? (
                        <>
                          <Loader2 size={12} className="spinner" />
                          <span>Validating...</span>
                        </>
                      ) : localPathValidation.valid === true ? (
                        <>
                          <Check size={12} />
                          <span>Found atopile{localPathValidation.version ? ` v${localPathValidation.version}` : ''}</span>
                        </>
                      ) : localPathValidation.valid === false ? (
                        <>
                          <X size={12} />
                          <span>{localPathValidation.error || 'Invalid path'}</span>
                        </>
                      ) : null}
                    </div>
                  )}
                </div>
              )}

              {/* Current Status */}
              {!atopile?.isInstalling && atopile?.currentVersion && (
                <div className="settings-status">
                  <Check size={12} className="status-ok" />
                  <span>
                    {atopile.source === 'local'
                      ? `Using local: ${atopile.localPath?.split('/').pop() || 'atopile'}`
                      : `v${atopile.currentVersion} installed`
                    }
                  </span>
                </div>
              )}

              {/* Parallel Builds Setting */}
              <div className="settings-group">
                <div className="settings-row">
                  <span className="settings-label-title">Parallel builds</span>
                  <div className="settings-inline-control">
                    {maxConcurrentUseDefault ? (
                      <button
                        className="settings-value-btn"
                        onClick={() => setMaxConcurrentUseDefault(false)}
                        title="Click to set custom limit"
                      >
                        Auto ({defaultMaxConcurrent})
                      </button>
                    ) : (
                      <div className="settings-custom-input">
                        <input
                          type="number"
                          className="settings-input small"
                          min={1}
                          max={32}
                          value={maxConcurrentValue}
                          onChange={(e) => {
                            const value = Math.max(1, Math.min(32, parseInt(e.target.value) || 1));
                            setMaxConcurrentValue(value);
                            action('setMaxConcurrentSetting', {
                              useDefault: false,
                              customValue: value
                            });
                          }}
                        />
                        <button
                          className="settings-reset-btn"
                          onClick={() => {
                            setMaxConcurrentUseDefault(true);
                            action('setMaxConcurrentSetting', {
                              useDefault: true,
                              customValue: null
                            });
                          }}
                          title="Reset to auto"
                        >
                          Auto
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="settings-divider" />

              {/* Developer Settings */}
              <div className="settings-section-header">Developer</div>
              <div className="settings-group">
                <div className="settings-row">
                  <span className="settings-label-title">Show all problems</span>
                  <div className="settings-inline-control">
                    <label className="settings-toggle">
                      <input
                        type="checkbox"
                        checked={developerMode || false}
                        onChange={(e) => action('setDeveloperMode', { enabled: e.target.checked })}
                      />
                      <span className="settings-toggle-slider" />
                    </label>
                  </div>
                </div>
                <div className="settings-hint">
                  Show internal developer messages in Problems panel
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}
