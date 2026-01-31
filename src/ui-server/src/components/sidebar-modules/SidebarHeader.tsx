/**
 * SidebarHeader component - Header with logo, version, and settings dropdown.
 *
 * Simplified version selector with:
 * - Toggle for "Use local atopile" that syncs bidirectionally with atopile.ato setting
 * - Manual path input
 * - Health indicators (green=healthy, red=broken, blue=installing)
 *
 * Toggle behavior:
 * - If atopile.ato has any path → toggle is ON
 * - If atopile.ato is cleared → toggle is OFF
 * - Turning toggle OFF clears atopile.ato
 */

import { useEffect, useRef, useState } from 'react';
import { Settings, FolderOpen, Loader2, AlertCircle, Check, X } from 'lucide-react';
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
  // Actual running atopile info
  actualVersion?: string | null;
  actualSource?: string | null;  // 'explicit-path', 'from-setting', or 'default'
  actualBinaryPath?: string | null;
  fromBranch?: string | null;  // Git branch when installed via uv from git
  fromSpec?: string | null;  // The pip/uv spec (for from-setting mode)
  // User selection state
  isInstalling?: boolean;
  installProgress?: {
    message?: string;
    percent?: number;
  } | null;
  error?: string | null;
  source?: 'release' | 'local';
  localPath?: string | null;
}

interface SidebarHeaderProps {
  atopile?: AtopileState;
  isConnected?: boolean;
}

export function SidebarHeader({ atopile, isConnected = true }: SidebarHeaderProps) {
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

  // Debounce ref for path input
  const pathDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Max concurrent builds setting
  const detectedCores = typeof navigator !== 'undefined' ? navigator.hardwareConcurrency || 4 : 4;
  const [maxConcurrentUseDefault, setMaxConcurrentUseDefault] = useState(true);
  const [maxConcurrentValue, setMaxConcurrentValue] = useState(detectedCores);
  const [defaultMaxConcurrent, setDefaultMaxConcurrent] = useState(detectedCores);

  // Local state for toggle (allows UI to work even when backend is down)
  const [useLocalAtopile, setUseLocalAtopile] = useState(atopile?.source === 'local');
  // Track if we've received settings from the extension (to avoid overwriting with backend state)
  const [settingsReceived, setSettingsReceived] = useState(false);
  // Track when user is actively changing the toggle (to ignore echo responses)
  const userChangingToggleRef = useRef(false);

  // Request settings from the extension on mount
  useEffect(() => {
    // Request current atopile settings from the extension
    postMessage({ type: 'getAtopileSettings' });

    // After 3 seconds, assume initialization is done (even if no response)
    const timeout = setTimeout(() => {
      setSettingsReceived(true);
    }, 3000);

    // Listen for the response
    const unsubscribe = onExtensionMessage((message: ExtensionToWebviewMessage) => {
      if (message.type === 'atopileSettingsResponse') {
        const { atoPath } = message.settings;
        console.log('[SidebarHeader] Received atopile settings from extension:', message.settings);
        // Update toggle to match settings, unless user just changed it
        // (ignore echo responses from our own toggle changes)
        if (!userChangingToggleRef.current) {
          const shouldUseLocal = !!atoPath;
          setUseLocalAtopile(shouldUseLocal);
        }
        setSettingsReceived(true);
        // Update the input if user is not actively typing
        if (!inputFocusedRef.current) {
          setLocalPathInput(atoPath || '');
        }
      }
    });

    return () => {
      unsubscribe();
      clearTimeout(timeout);
    };
  }, []);

  // Sync toggle state when backend state changes (but only after initial settings or if no settings received)
  useEffect(() => {
    // Only sync from backend if we haven't received settings from extension
    // OR if the backend explicitly tells us the source
    if (atopile?.source !== undefined && !settingsReceived) {
      setUseLocalAtopile(atopile.source === 'local');
    }
  }, [atopile?.source, settingsReceived]);

  // Local state for path input (controlled input needs synchronous state updates)
  const [localPathInput, setLocalPathInput] = useState(atopile?.localPath || '');
  // Track if input is focused to prevent external sync from overwriting user typing
  // Use a ref so it's always current in closures (avoids stale state in event handlers)
  const inputFocusedRef = useRef(false);

  // Sync local input state when store value changes externally
  // BUT only when the input is not focused (user not actively typing)
  // AND only when backend provides a non-empty path (don't clear user input when backend is down)
  useEffect(() => {
    if (!inputFocusedRef.current && atopile?.localPath && atopile.localPath !== localPathInput) {
      setLocalPathInput(atopile.localPath);
    }
  }, [atopile?.localPath]);

  // Check if toggle is ON but no path entered yet
  // This is a "needs configuration" state - user turned on local but hasn't set it up
  const needsLocalConfig = useLocalAtopile && !localPathInput;

  // Debug logging
  console.log('[SidebarHeader] State:', {
    useLocalAtopile,
    localPathInput,
    actualSource: atopile?.actualSource,
    actualBinaryPath: atopile?.actualBinaryPath,
  });

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

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (pathDebounceRef.current) {
        clearTimeout(pathDebounceRef.current);
      }
    };
  }, []);

  // Listen for browse path result from VS Code extension
  useEffect(() => {
    const unsubscribe = onExtensionMessage((message: ExtensionToWebviewMessage) => {
      if (message.type === 'browseAtopilePathResult' && message.path) {
        // Update local state
        setLocalPathInput(message.path);
        // Save to VS Code settings
        postMessage({
          type: 'atopileSettings',
          atopile: {
            source: 'local',
            localPath: message.path,
          },
        });
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
        };
      };

      const result = message?.result;

      if (result?.setting) {
        setMaxConcurrentUseDefault(result.setting.use_default);
        setMaxConcurrentValue(result.setting.custom_value || result.setting.default_value);
        setDefaultMaxConcurrent(result.setting.default_value);
      }
    };
    window.addEventListener('atopile:action_result', handleActionResult);
    return () => window.removeEventListener('atopile:action_result', handleActionResult);
  }, []);

  // Handle toggle change
  const handleToggleChange = (checked: boolean) => {
    // Mark that user is changing toggle (ignore echo responses for 1 second)
    userChangingToggleRef.current = true;
    setTimeout(() => {
      userChangingToggleRef.current = false;
    }, 1000);

    // Update local state immediately (works even when backend is down)
    setUseLocalAtopile(checked);

    if (checked) {
      // Switch to local mode
      action('setAtopileSource', { source: 'local' });
      // Also save to VS Code settings with current path
      postMessage({
        type: 'atopileSettings',
        atopile: {
          source: 'local',
          localPath: localPathInput || null,
        },
      });
    } else {
      // Switch back to default (extension-managed uv) - just clear atopile.ato
      postMessage({
        type: 'atopileSettings',
        atopile: {
          source: 'release',
          localPath: null,  // Clear the ato setting
        },
      });
      // Update backend state
      action('setAtopileSource', { source: 'release' });
    }
  };

  // Determine health status
  const getHealthStatus = (): 'installing' | 'healthy' | 'unhealthy' | 'unknown' | 'needs-config' | 'disconnected' => {
    // Check for errors first - even when disconnected, show the error
    if (atopile?.error) {
      console.log('[SidebarHeader] getHealthStatus: unhealthy -', atopile.error);
      return 'unhealthy';
    }
    // Check if installing - even when disconnected, show the installing status
    if (atopile?.isInstalling) {
      console.log('[SidebarHeader] getHealthStatus: installing');
      return 'installing';
    }
    // Check if disconnected from backend
    // If we've received settings but still not connected, it's likely a failure
    if (!isConnected) {
      if (settingsReceived) {
        console.log('[SidebarHeader] getHealthStatus: unhealthy - backend not connected');
        return 'unhealthy';
      }
      console.log('[SidebarHeader] getHealthStatus: disconnected');
      return 'disconnected';
    }
    // Check if toggle is ON but needs configuration (no path entered yet)
    if (needsLocalConfig) {
      console.log('[SidebarHeader] getHealthStatus: needs-config');
      return 'needs-config';
    }
    if (atopile?.actualVersion) {
      console.log('[SidebarHeader] getHealthStatus: healthy - v' + atopile.actualVersion);
      return 'healthy';
    }
    console.log('[SidebarHeader] getHealthStatus: unknown');
    return 'unknown';
  };

  const healthStatus = getHealthStatus();
  console.log('[SidebarHeader] Final healthStatus:', healthStatus);

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
            className={`icon-btn${showSettings ? ' active' : ''}${healthStatus === 'unhealthy' ? ' has-error' : ''}`}
            onClick={() => setShowSettings(!showSettings)}
            title="Settings"
          >
            <Settings size={14} />
            {healthStatus === 'unhealthy' && (
              <span className="settings-error-dot" />
            )}
          </button>
          {showSettings && (
            <div className="settings-dropdown">
              {/* Health Status Indicator - Always visible at top */}
              <div className="settings-group">
                <div className={`atopile-health-status health-${healthStatus}`}>
                  {healthStatus === 'installing' && (
                    <>
                      <Loader2 size={14} className="spinner" />
                      <span className="health-message">
                        {atopile?.installProgress?.message || 'Installing atopile...'}
                      </span>
                    </>
                  )}
                  {healthStatus === 'needs-config' && (
                    <>
                      <AlertCircle size={14} />
                      <span className="health-message">
                        Enter a path to use local atopile
                      </span>
                    </>
                  )}
                  {healthStatus === 'healthy' && (
                    <>
                      <Check size={14} />
                      <span className="health-message">
                        {(() => {
                          const version = atopile?.actualVersion || '?';
                          const source = atopile?.actualSource;

                          // explicit-path: show version + path
                          if (source === 'explicit-path') {
                            const path = atopile?.localPath || atopile?.actualBinaryPath || '';
                            return `Using atopile v${version} (${path})`;
                          }

                          // from-setting: show version + branch or spec
                          if (source === 'from-setting') {
                            if (atopile?.fromBranch) {
                              return `Using atopile v${version} (${atopile.fromBranch})`;
                            }
                            if (atopile?.fromSpec) {
                              return `Using atopile v${version} (${atopile.fromSpec})`;
                            }
                          }

                          // default: just show version
                          return `Using atopile v${version}`;
                        })()}
                      </span>
                    </>
                  )}
                  {healthStatus === 'unhealthy' && (
                    <>
                      <X size={14} />
                      <span className="health-message">
                        {atopile?.error || 'Unable to connect to atopile backend.'}
                      </span>
                    </>
                  )}
                  {healthStatus === 'unknown' && (
                    <>
                      <Loader2 size={14} className="spinner" />
                      <span className="health-message">Checking atopile status...</span>
                    </>
                  )}
                  {healthStatus === 'disconnected' && (
                    <>
                      <Loader2 size={14} className="spinner" />
                      <span className="health-message">
                        Connecting to backend...
                      </span>
                    </>
                  )}
                </div>
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
                    : atopile?.actualSource === 'from-setting'
                      ? atopile?.fromBranch
                        ? `Using atopile from branch: ${atopile.fromBranch}`
                        : atopile?.fromSpec
                          ? `Using atopile from: ${atopile.fromSpec}`
                          : 'Using a custom atopile source'
                      : 'Using the standard atopile release'}
                </span>
              </div>

              {/* Local Path Section - Only visible when toggle is on */}
              {useLocalAtopile && (
                <div className="settings-group local-path-section">
                  <label className="settings-label">
                    <span className="settings-label-title">Path to atopile:</span>
                  </label>
                  <div className="settings-path-input">
                    <input
                      type="text"
                      className="settings-input"
                      placeholder="/atopile/.venv/bin/ato"
                      value={localPathInput}
                      title={localPathInput || "/atopile/.venv/bin/ato"}
                      onFocus={() => { inputFocusedRef.current = true; }}
                      onBlur={() => { inputFocusedRef.current = false; }}
                      onChange={(e) => {
                        const newValue = e.target.value;
                        // Update local state immediately for responsive input
                        setLocalPathInput(newValue);
                        // Debounce the save to VS Code settings
                        if (pathDebounceRef.current) {
                          clearTimeout(pathDebounceRef.current);
                        }
                        pathDebounceRef.current = setTimeout(() => {
                          postMessage({
                            type: 'atopileSettings',
                            atopile: {
                              source: 'local',
                              localPath: newValue || null,
                            },
                          });
                        }, 500);
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
