/**
 * SidebarHeader component - Header with logo, version, and settings dropdown.
 *
 * Simplified version selector with:
 * - Toggle for "Use local atopile"
 * - Auto-detect local installations in workspace
 * - Health indicators (green=healthy, red=broken, blue=installing)
 */

import { useEffect, useRef, useState } from 'react';
import { Settings, FolderOpen, Loader2, AlertCircle, Check, X, RotateCcw } from 'lucide-react';
import { sendAction } from '../../api/websocket';
import { postMessage, onExtensionMessage, type ExtensionToWebviewMessage } from '../../api/vscodeApi';

// Send action to backend via WebSocket (or VS Code extension for special actions)
const action = (name: string, data?: Record<string, unknown>) => {
  if (name === 'openUrl' && data && 'url' in data) {
    const url = (data as { url?: string }).url;
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
      return;
    }
  }
  // browseAtopilePath needs to be handled by VS Code extension for native folder picker
  if (name === 'browseAtopilePath') {
    postMessage({ type: 'browseAtopilePath' });
    return;
  }
  sendAction(name, data);
};

interface AtopileState {
  // Actual installed atopile (source of truth for builds)
  actualVersion?: string | null;
  actualSource?: string | null;
  actualBinaryPath?: string | null;  // The actual binary path being used
  // User selection state
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
  // Health check status
  healthStatus?: 'checking' | 'healthy' | 'unhealthy' | null;
}

interface SidebarHeaderProps {
  atopile?: AtopileState;
}

export function SidebarHeader({ atopile }: SidebarHeaderProps) {
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

  // Use local toggle state - derived from atopile.source
  const useLocalAtopile = atopile?.source === 'local';

  // Local path validation state
  const [localPathValidation, setLocalPathValidation] = useState<{
    isValidating: boolean;
    valid: boolean | null;
    version: string | null;
    error: string | null;
  }>({ isValidating: false, valid: null, version: null, error: null });
  const validateDebounceRef = useRef<NodeJS.Timeout | null>(null);

  // Check if a path matches the currently running binary
  const pathMatchesActualBinary = (path: string): boolean => {
    if (!atopile?.actualBinaryPath) return false;
    // Normalize paths for comparison (remove trailing slashes, handle venv paths)
    const normalizedPath = path.replace(/\/+$/, '');
    const normalizedActual = atopile.actualBinaryPath.replace(/\/+$/, '');
    // Direct match
    if (normalizedPath === normalizedActual) return true;
    // Check if the selected path is a parent directory containing the actual binary
    // e.g., selecting "/path/to/atopile" should match "/path/to/atopile/.venv/bin/ato"
    if (normalizedActual.startsWith(normalizedPath + '/')) return true;
    // Check if selecting a venv's bin/ato
    if (normalizedPath.endsWith('/bin/ato') && normalizedActual === normalizedPath) return true;
    return false;
  };

  // Pending restart state - when user selects a new atopile but needs to restart
  // Computed based on whether localPath (from settings) matches actualBinaryPath
  const pendingRestartNeeded = useLocalAtopile &&
    atopile?.localPath != null &&
    atopile?.actualBinaryPath != null &&
    !pathMatchesActualBinary(atopile.localPath);

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

  // Refresh detected installations when settings open
  useEffect(() => {
    if (showSettings) {
      action('refreshDetectedInstallations');
    }
  }, [showSettings]);

  // Validate local path when it changes
  useEffect(() => {
    if (!useLocalAtopile || !atopile?.localPath) {
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
  }, [useLocalAtopile, atopile?.localPath]);

  // Listen for browse path result from VS Code extension
  useEffect(() => {
    const unsubscribe = onExtensionMessage((message: ExtensionToWebviewMessage) => {
      if (message.type === 'browseAtopilePathResult' && message.path) {
        // Validate and select the path (version will be set after validation)
        action('setAtopileLocalPath', { path: message.path });
        // Save to settings immediately
        postMessage({
          type: 'atopileSettings',
          atopile: {
            source: 'local',
            localPath: message.path,
          },
        });
        // Restart status is computed from state, no need to track manually
      }
    });

    return unsubscribe;
  }, []);

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

        // If validation succeeded, save settings
        if (result.valid && atopile?.localPath) {
          postMessage({
            type: 'atopileSettings',
            atopile: {
              source: 'local',
              localPath: atopile.localPath,
            },
          });
          // Restart status is computed from state, no need to track manually
        }
      }
    };
    window.addEventListener('atopile:action_result', handleActionResult);
    return () => window.removeEventListener('atopile:action_result', handleActionResult);
  }, [atopile?.localPath]);

  // Helper to select a local installation
  const selectLocalInstallation = (path: string, _version: string | null) => {
    // Update backend state
    action('setAtopileLocalPath', { path });
    // Save to VS Code settings (will be used on next startup)
    postMessage({
      type: 'atopileSettings',
      atopile: {
        source: 'local',
        localPath: path,
      },
    });
    // No need to track pending restart manually - it's computed from state
  };

  // Handle toggle change
  const handleToggleChange = (checked: boolean) => {
    if (checked) {
      // Switch to local mode
      action('setAtopileSource', { source: 'local' });
      // Refresh detected installations
      action('refreshDetectedInstallations');
      // If we already have a local path, save settings
      if (atopile?.localPath) {
        selectLocalInstallation(atopile.localPath, localPathValidation.version);
      }
    } else {
      // Switch back to release mode (default)
      action('setAtopileSource', { source: 'release' });
      // Refresh available versions
      action('refreshAtopileVersions');
      // Save to VS Code settings
      postMessage({
        type: 'atopileSettings',
        atopile: {
          source: 'release',
        },
      });
      // Restart is now computed from state, no need to track manually
    }
  };

  // Handle restart button click - restarts only the atopile extension, not the entire VS Code window
  const handleRestartClick = () => {
    postMessage({ type: 'restartExtension' });
  };

  // Determine health status
  const getHealthStatus = (): 'installing' | 'healthy' | 'unhealthy' | 'unknown' | 'restart-needed' => {
    // Check if restart is needed first (settings differ from actual binary)
    if (pendingRestartNeeded) {
      return 'restart-needed';
    }
    if (atopile?.isInstalling) {
      return 'installing';
    }
    if (atopile?.error) {
      return 'unhealthy';
    }
    if (atopile?.actualVersion) {
      return 'healthy';
    }
    return 'unknown';
  };

  const healthStatus = getHealthStatus();

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
              {/* Health Status Indicator - Always visible at top */}
              <div className="settings-group">
                {healthStatus === 'restart-needed' ? (
                  <div className="atopile-restart-container">
                    <div className="atopile-health-status health-restart-needed">
                      <AlertCircle size={14} />
                      <span className="health-message">
                        Restart extension host to switch to selected atopile
                      </span>
                    </div>
                    <button
                      className="atopile-restart-button"
                      onClick={handleRestartClick}
                      title="Restart the atopile backend to apply new settings"
                    >
                      <RotateCcw size={14} />
                      <span>Restart</span>
                    </button>
                  </div>
                ) : (
                  <div className={`atopile-health-status health-${healthStatus}`}>
                    {healthStatus === 'installing' && (
                      <>
                        <Loader2 size={14} className="spinner" />
                        <span className="health-message">
                          {atopile?.installProgress?.message || 'Installing atopile...'}
                        </span>
                      </>
                    )}
                    {healthStatus === 'healthy' && (
                      <>
                        <Check size={14} />
                        <span className="health-message">
                          {useLocalAtopile
                            ? `Using local atopile v${atopile?.actualVersion || '?'}`
                            : `Using atopile v${atopile?.actualVersion || '?'}`}
                        </span>
                      </>
                    )}
                    {healthStatus === 'unhealthy' && (
                      <>
                        <AlertCircle size={14} />
                        <span className="health-message">
                          {atopile?.error || 'atopile is not working'}
                        </span>
                      </>
                    )}
                    {healthStatus === 'unknown' && (
                      <>
                        <Loader2 size={14} className="spinner" />
                        <span className="health-message">Checking atopile status...</span>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Use Local Toggle */}
              <div className="settings-group">
                <div className="settings-row settings-toggle-row">
                  <span className="settings-label-title">Use local atopile</span>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={useLocalAtopile}
                      onChange={(e) => handleToggleChange(e.target.checked)}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>
                <span className="settings-hint">
                  {useLocalAtopile
                    ? 'Using a local installation from filesystem'
                    : 'Using the standard atopile from PyPI'}
                </span>
              </div>

              {/* Local Path Section - Only visible when toggle is on */}
              {useLocalAtopile && (
                <div className="settings-group local-path-section">
                  {/* Detected installations - only show if there are any */}
                  {(atopile?.detectedInstallations?.length ?? 0) > 0 && (
                    <div className="detected-installations">
                      <span className="detected-label">Environments detected in workspace:</span>
                      <div className="detected-list">
                        {atopile?.detectedInstallations?.map((inst, i) => {
                          // Extract the directory name above .venv (e.g., "atopile_reorg" from "/path/to/atopile_reorg/.venv/bin/ato")
                          const pathParts = inst.path.split('/');
                          const venvIndex = pathParts.findIndex(p => p === '.venv' || p === 'venv');
                          const projectName = venvIndex > 0 ? pathParts[venvIndex - 1] : pathParts[pathParts.length - 1];

                          return (
                            <button
                              key={i}
                              className={`detected-item${atopile?.localPath === inst.path ? ' active' : ''}`}
                              onClick={() => selectLocalInstallation(inst.path, inst.version ?? null)}
                              title={inst.path}
                            >
                              <span className="detected-project">{projectName}</span>
                              {inst.version && <span className="detected-version">v{inst.version}</span>}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Manual path input */}
                  <label className="settings-label">
                    <span className="settings-label-title">
                      {(atopile?.detectedInstallations?.length ?? 0) > 0
                        ? 'Or enter path manually:'
                        : 'Enter path to atopile:'}
                    </span>
                  </label>
                  <div className="settings-path-input">
                    <input
                      type="text"
                      className={`settings-input${localPathValidation.valid === true ? ' valid' : ''}${localPathValidation.valid === false ? ' invalid' : ''}`}
                      placeholder="/path/to/atopile or ato binary"
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
