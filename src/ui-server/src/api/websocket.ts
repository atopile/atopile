/**
 * WebSocket client for real-time state updates from the Python backend.
 *
 * The backend broadcasts full state on every change. This client connects
 * to the WebSocket endpoint and updates the Zustand store.
 */

import { useStore } from '../store';
import type { AppState, Build, BuildStatus } from '../types/build';
import type { EventMessage } from '../types/gen/generated';
import { EventMessageType, EventType } from '../types/gen/generated';
import { api } from './client';
import { WS_STATE_URL, getWorkspaceFolders } from './config';
import { postMessage } from './vscodeApi';

// Reconnection settings
const RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 10000; // Reduced from 30s for faster reconnection
const RECONNECT_BACKOFF_MULTIPLIER = 1.5;
const CONNECTION_TIMEOUT_MS = 5000; // Timeout for connection handshake

// Message types from backend
interface StateMessage {
  type: 'state';
  data: AppState;
}

interface ActionResultMessage {
  type: 'action_result';
  action: string;
  payload?: Record<string, unknown>;  // Original request payload for tracking
  result?: {
    success: boolean;
    error?: string;
    [key: string]: unknown;
  };
  // Legacy direct fields (for backwards compatibility)
  success?: boolean;
  error?: string;
}

type BackendMessage = StateMessage | ActionResultMessage | EventMessage;

// WebSocket connection state
let ws: WebSocket | null = null;
let reconnectAttempts = 0;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let connectionTimeout: ReturnType<typeof setTimeout> | null = null;
let isIntentionallyClosed = false;
let requestCounter = 0;
const pendingRequests = new Map<string, {
  resolve: (message: ActionResultMessage) => void;
  reject: (error: Error) => void;
  timeoutId: ReturnType<typeof setTimeout>;
}>();

/**
 * Clean up any pending timeouts and close the current WebSocket.
 */
function cleanup(): void {
  if (connectionTimeout) {
    clearTimeout(connectionTimeout);
    connectionTimeout = null;
  }
  if (pendingRequests.size > 0) {
    for (const [requestId, pending] of pendingRequests.entries()) {
      clearTimeout(pending.timeoutId);
      pending.reject(new Error('WebSocket disconnected'));
      pendingRequests.delete(requestId);
    }
  }
  if (ws) {
    // Remove handlers to prevent callbacks during cleanup
    ws.onopen = null;
    ws.onmessage = null;
    ws.onclose = null;
    ws.onerror = null;
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
    ws = null;
  }
}

/**
 * Connect to the backend WebSocket.
 * Automatically reconnects on disconnect.
 */
export function connect(): void {
  if (ws?.readyState === WebSocket.OPEN) {
    console.log('[WS] Already connected');
    return;
  }

  // If stuck in CONNECTING state, clean up and try again
  if (ws?.readyState === WebSocket.CONNECTING) {
    console.log('[WS] Previous connection stuck, cleaning up');
    cleanup();
  }

  isIntentionallyClosed = false;
  console.log(`[WS] Connecting to ${WS_STATE_URL}`);

  try {
    ws = new WebSocket(WS_STATE_URL);

    ws.onopen = handleOpen;
    ws.onmessage = handleMessage;
    ws.onclose = handleClose;
    ws.onerror = handleError;

    // Set connection timeout - if handshake doesn't complete, force reconnect
    connectionTimeout = setTimeout(() => {
      if (ws?.readyState === WebSocket.CONNECTING) {
        console.warn('[WS] Connection timeout - handshake did not complete');
        cleanup();
        useStore.getState().setConnected(false);
        scheduleReconnect();
      }
    }, CONNECTION_TIMEOUT_MS);
  } catch (error) {
    console.error('[WS] Failed to create WebSocket:', error);
    scheduleReconnect();
  }
}

/**
 * Disconnect from the backend WebSocket.
 */
export function disconnect(): void {
  isIntentionallyClosed = true;

  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }

  cleanup();
  useStore.getState().setConnected(false);
  console.log('[WS] Disconnected');
}

/**
 * Send an action to the backend via WebSocket.
 */
export function sendAction(action: string, payload?: Record<string, unknown>): void {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.warn('[WS] Cannot send action - not connected');
    return;
  }

  ws.send(
    JSON.stringify({
      type: 'action',
      action,
      payload: payload || {},
    })
  );
}

/**
 * Send an action and await the corresponding action_result.
 */
export function sendActionWithResponse(
  action: string,
  payload: Record<string, unknown> = {},
  options?: { timeoutMs?: number }
): Promise<ActionResultMessage> {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return Promise.reject(new Error('WebSocket not connected'));
  }

  requestCounter += 1;
  const requestId = `${Date.now()}-${requestCounter}`;
  const timeoutMs = options?.timeoutMs ?? 10000;

  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      pendingRequests.delete(requestId);
      reject(new Error(`Action timeout: ${action}`));
    }, timeoutMs);

    pendingRequests.set(requestId, { resolve, reject, timeoutId });
    sendAction(action, { ...payload, requestId });
  });
}

/**
 * Check if WebSocket is connected.
 */
export function isConnected(): boolean {
  return ws?.readyState === WebSocket.OPEN;
}

// --- Internal handlers ---

function handleOpen(): void {
  // Clear connection timeout since we connected successfully
  if (connectionTimeout) {
    clearTimeout(connectionTimeout);
    connectionTimeout = null;
  }
  console.log('[WS] Connected');
  reconnectAttempts = 0;
  useStore.getState().setConnected(true);

  // Notify VS Code extension of connection status
  postMessage({ type: 'connectionStatus', isConnected: true });

  // Send workspace folders to backend if provided by VS Code extension
  const workspaceFolders = getWorkspaceFolders();
  if (workspaceFolders.length > 0) {
    console.log('[WS] Sending workspace folders:', workspaceFolders);
    sendAction('setWorkspaceFolders', { folders: workspaceFolders });
  }

  // Get atopile config (including actual version) - this clears any "installing" state
  sendAction('getAtopileConfig');

  void refreshProjects();
  void refreshBuilds();
  void fetchLogViewCurrentId();
}

function handleMessage(event: MessageEvent): void {
  try {
    const message = JSON.parse(event.data) as BackendMessage;

    switch (message.type) {
      case 'state':
        // Full state replacement from backend
        // Note: Backend's to_frontend_dict() converts all keys to camelCase
        {
          const state = message.data as AppState;

          // Extract one-shot open signals before replacing state
          const { openFile, openFileLine, openFileColumn, openLayout, openKicad, open3D, ...stateWithoutSignals } = state;

          // Update store with state (excluding one-shot signals)
          useStore.getState().replaceState(stateWithoutSignals);

          // Forward open signals to VS Code extension (one-shot actions)
          if (openFile || openLayout || openKicad || open3D) {
            postMessage({
              type: 'openSignals',
              openFile: openFile ?? null,
              openFileLine: openFileLine ?? null,
              openFileColumn: openFileColumn ?? null,
              openLayout: openLayout ?? null,
              openKicad: openKicad ?? null,
              open3d: open3D ?? null,
            });
          }

          // NOTE: Don't forward backend atopile state to VS Code settings here.
          // The backend state is informational (what's currently running).
          // User settings are only saved when explicitly changed in SidebarHeader.
        }
        break;

      case 'action_result':
        // Action response (success/failure)
        // Result is nested in message.result from backend
        const result = message.result || message;
        const requestId = typeof message.payload?.requestId === 'string'
          ? message.payload.requestId
          : null;
        if (requestId && pendingRequests.has(requestId)) {
          const pending = pendingRequests.get(requestId)!;
          clearTimeout(pending.timeoutId);
          pendingRequests.delete(requestId);
          if (result.success) {
            pending.resolve(message);
          } else {
            pending.reject(new Error(String(result.error || 'Action failed')));
          }
        }
        if (!result.success) {
          console.error(`[WS] Action failed: ${message.action}`, result.error);
        }
        if (message.action === 'build' || message.action === 'cancelBuild') {
          void refreshBuilds();
        }
        // Auto-switch log viewer to the newly queued build
        if (message.action === 'build' && result.success) {
          const r = result as Record<string, unknown>;
          const singleId = r.build_id ?? r.buildId;
          const multiIds = r.build_ids ?? r.buildIds;
          const buildId = typeof singleId === 'string'
            ? singleId
            : (Array.isArray(multiIds) && typeof multiIds[0] === 'string' ? multiIds[0] : null);
          if (buildId) {
            useStore.getState().setLogViewerBuildId(buildId);
            sendAction('setLogViewCurrentId', { buildId, stage: null });
          }
        }
        if (typeof window !== 'undefined') {
          window.dispatchEvent(
            new CustomEvent('atopile:action_result', { detail: message })
          );
        }
        break;
      case EventMessageType.Event:
        handleEventMessage(message);
        break;

      default:
        console.warn('[WS] Unknown message type:', message);
    }
  } catch (error) {
    console.error('[WS] Failed to parse message:', error, event.data);
  }
}

async function refreshProjects(): Promise<void> {
  try {
    const response = await api.projects.list();
    useStore.getState().setProjects(response.projects || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh projects:', error);
  }
}

function getSelectedTargetName(): string | null {
  const state = useStore.getState();
  if (!state.selectedProjectRoot) return null;
  if (state.selectedTargetNames?.length) return state.selectedTargetNames[0] ?? null;
  const project = state.projects.find((p) => p.root === state.selectedProjectRoot);
  return project?.targets?.[0]?.name ?? null;
}

async function refreshDependencies(projectRoot?: string | null): Promise<void> {
  const root = projectRoot || useStore.getState().selectedProjectRoot;
  if (!root) return;
  try {
    const response = await api.dependencies.list(root);
    useStore.getState().setProjectDependencies(root, response.dependencies || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh dependencies:', error);
  }
}

async function refreshBom(): Promise<void> {
  const state = useStore.getState();
  if (!state.selectedProjectRoot) return;
  const targetName = getSelectedTargetName();
  if (!targetName) return;
  try {
    state.setLoadingBom(true);
    const response = await api.bom.get(state.selectedProjectRoot, targetName);
    state.setBomData(response || null);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to fetch BOM';
    state.setBomError(message);
  }
}

async function refreshVariables(): Promise<void> {
  const state = useStore.getState();
  if (!state.selectedProjectRoot) return;
  const targetName = getSelectedTargetName();
  if (!targetName) return;
  try {
    state.setLoadingVariables(true);
    const response = await api.variables.get(state.selectedProjectRoot, targetName);
    state.setVariablesData(response || null);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Failed to fetch variables';
    state.setVariablesError(message);
  }
}

async function refreshPackages(): Promise<void> {
  const state = useStore.getState();
  try {
    state.setLoadingPackages(true);
    const response = await api.packages.summary();
    state.setPackages(response.packages || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh packages:', error);
    state.setPackages([]);
  }
}

async function refreshStdlib(): Promise<void> {
  const state = useStore.getState();
  try {
    state.setLoadingStdlib(true);
    const response = await api.stdlib.list();
    state.setStdlibItems(response.items || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh stdlib:', error);
    state.setStdlibItems([]);
  }
}

async function refreshProblems(): Promise<void> {
  const state = useStore.getState();
  try {
    state.setLoadingProblems(true);
    const response = await api.problems.list();
    state.setProblems(response.problems || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh problems:', error);
    state.setProblems([]);
  }
}

function normalizeStage(stage: Record<string, unknown>): Record<string, unknown> {
  return {
    ...stage,
    stageId:
      (stage.stageId as string | undefined) ??
      (stage.stage_id as string | undefined),
    displayName:
      (stage.displayName as string | undefined) ??
      (stage.display_name as string | undefined),
    elapsedSeconds:
      (stage.elapsedSeconds as number | undefined) ??
      (stage.elapsed_seconds as number | undefined),
  };
}

function normalizeBuild(raw: Build | Record<string, unknown>): Build {
  const rawData = raw as Record<string, unknown>;
  const stages = Array.isArray(rawData.stages)
    ? rawData.stages.map((stage) =>
      normalizeStage(stage as Record<string, unknown>)
    )
    : rawData.stages;

  const name =
    (rawData.name as string | undefined) ??
    (rawData.build_name as string | undefined) ??
    (rawData.buildName as string | undefined) ??
    (rawData.target as string | undefined) ??
    'unknown';
  const displayName =
    (rawData.displayName as string | undefined) ??
    (rawData.display_name as string | undefined) ??
    name;
  const projectName =
    (rawData.projectName as string | null | undefined) ??
    (rawData.project_name as string | null | undefined) ??
    null;
  const status =
    (rawData.status as BuildStatus | undefined) ??
    'queued';
  const elapsedSeconds =
    (rawData.elapsedSeconds as number | undefined) ??
    (rawData.elapsed_seconds as number | undefined) ??
    0;
  const warnings =
    (rawData.warnings as number | undefined) ??
    0;
  const errors =
    (rawData.errors as number | undefined) ??
    0;
  const returnCode =
    (rawData.returnCode as number | null | undefined) ??
    (rawData.return_code as number | null | undefined) ??
    null;
  const error =
    (rawData.error as string | undefined) ??
    (rawData.error_message as string | undefined) ??
    (rawData.errorMessage as string | undefined);

  return {
    name,
    displayName,
    projectName,
    status,
    elapsedSeconds,
    warnings,
    errors,
    returnCode,
    error,
    buildId:
      (rawData.buildId as string | undefined) ??
      (rawData.build_id as string | undefined),
    projectRoot:
      (rawData.projectRoot as string | undefined) ??
      (rawData.project_root as string | undefined),
    target:
      (rawData.target as string | undefined),
    entry:
      (rawData.entry as string | undefined),
    startedAt:
      (rawData.startedAt as number | undefined) ??
      (rawData.started_at as number | undefined),
    totalStages:
      (rawData.totalStages as number | undefined) ??
      (rawData.total_stages as number | undefined),
    logDir:
      (rawData.logDir as string | undefined) ??
      (rawData.log_dir as string | undefined),
    logFile:
      (rawData.logFile as string | undefined) ??
      (rawData.log_file as string | undefined),
    queuePosition:
      (rawData.queuePosition as number | undefined) ??
      (rawData.queue_position as number | undefined),
    stages: stages as Build['stages'],
  };
}

function getBuildKey(build: Build): string {
  const project = build.projectRoot || build.projectName || 'unknown';
  const target = build.target || build.name || 'default';
  return `${project}:${target}`;
}

async function refreshBuilds(): Promise<void> {
  const state = useStore.getState();
  try {
    const previousBuildsById = new Map<string, Build>();
    for (const build of [...state.builds, ...state.queuedBuilds]) {
      if (build.buildId) {
        previousBuildsById.set(build.buildId, build);
      }
    }

    const [active, history] = await Promise.all([
      api.builds.active(),
      api.builds.history(),
    ]);
    const activeBuilds = (active.builds || []).map((build) =>
      normalizeBuild(build)
    );
    const smoothedActiveBuilds = activeBuilds.map((build) => {
      if (!build.buildId) return build;
      const previous = previousBuildsById.get(build.buildId);
      const hasStages = Array.isArray(build.stages) && build.stages.length > 0;
      const hadStages =
        Array.isArray(previous?.stages) && previous.stages.length > 0;
      if (!hasStages && hadStages && previous?.stages) {
        return {
          ...build,
          stages: previous.stages,
        };
      }
      return build;
    });
    const historyBuilds = (history.builds || []).map((build) =>
      normalizeBuild(build)
    );

    const activeKeys = new Set(smoothedActiveBuilds.map(getBuildKey));
    const recentHistoryByKey = new Map<string, Build>();
    const sortedHistory = [...historyBuilds].sort((a, b) => {
      const aTime = (a.startedAt ?? 0) as number;
      const bTime = (b.startedAt ?? 0) as number;
      return bTime - aTime;
    });
    for (const build of sortedHistory) {
      if (build.status === 'queued' || build.status === 'building') continue;
      const key = getBuildKey(build);
      if (activeKeys.has(key) || recentHistoryByKey.has(key)) continue;
      recentHistoryByKey.set(key, build);
    }
    const recentHistoryBuilds = [...recentHistoryByKey.values()];
    const queuedBuilds = [...smoothedActiveBuilds, ...recentHistoryBuilds];

    // Use active builds for queued display since /api/builds/queue is status-only.
    state.setBuilds(smoothedActiveBuilds);
    state.setQueuedBuilds(queuedBuilds);
    state.setBuildHistory(historyBuilds);
  } catch (error) {
    console.warn('[WS] Failed to refresh builds:', error);
  }
}

async function fetchLogViewCurrentId(): Promise<void> {
  try {
    const response = await sendActionWithResponse('getLogViewCurrentId');
    const buildId = typeof response.result?.buildId === 'string'
      ? response.result.buildId
      : null;
    const stage = typeof response.result?.stage === 'string'
      ? response.result.stage
      : null;
    if (buildId) {
      useStore.getState().setLogViewerBuildId(buildId);
    }
    window.dispatchEvent(
      new CustomEvent('atopile:log_view_stage_changed', { detail: { stage } })
    );
  } catch (error) {
    console.warn('[WS] Failed to fetch log view current ID:', error);
  }
}

function handleEventMessage(message: EventMessage): void {
  const data = message.data ?? {};
  const projectRoot =
    (typeof data.projectRoot === 'string' && data.projectRoot) ||
    (typeof data.project_root === 'string' && data.project_root) ||
    null;

  switch (message.event) {
    case EventType.OpenLayout: {
      const path = typeof data.path === 'string' ? data.path : null;
      postMessage({
        type: 'openSignals',
        openLayout: path,
        openKicad: null,
        open3d: null,
      });
      break;
    }
    case EventType.OpenKicad: {
      const path = typeof data.path === 'string' ? data.path : null;
      postMessage({
        type: 'openSignals',
        openLayout: null,
        openKicad: path,
        open3d: null,
      });
      break;
    }
    case EventType.Open3D: {
      const path = typeof data.path === 'string' ? data.path : null;
      postMessage({
        type: 'openSignals',
        openLayout: null,
        openKicad: null,
        open3d: path,
      });
      break;
    }
    case EventType.ProjectsChanged:
      void refreshProjects();
      break;
    case EventType.BuildsChanged:
      void refreshBuilds();
      break;
    case EventType.ProjectDependenciesChanged:
      // Clear all installing packages - a dependency change means install completed
      useStore.getState().clearInstallingPackages();
      void refreshDependencies(projectRoot);
      break;
    case EventType.BOMChanged:
      void refreshBom();
      break;
    case EventType.VariablesChanged:
      void refreshVariables();
      break;
    case EventType.PackagesChanged:
      // Check if this is an install error event
      if (data.error && data.package_id) {
        const packageId = data.package_id as string;
        const errorMsg = data.error as string;
        useStore.getState().setInstallError(packageId, errorMsg);
      }
      void refreshPackages();
      break;
    case EventType.StdlibChanged:
      void refreshStdlib();
      break;
    case EventType.ProblemsChanged:
      void refreshProblems();
      break;
    case 'atopile_config_changed':
      console.log('[WS] Received atopile_config_changed raw data:', JSON.stringify(data, null, 2));
      updateAtopileConfig(data);
      break;
    case EventType.LogViewCurrentIDChanged:
      {
        const buildId = typeof data.buildId === 'string' ? data.buildId : null;
        const stage = typeof data.stage === 'string' ? data.stage : null;
        useStore.getState().setLogViewerBuildId(buildId);
        window.dispatchEvent(
          new CustomEvent('atopile:log_view_stage_changed', { detail: { stage } })
        );
      }
      break;
    default:
      break;
  }
}

function handleClose(event: CloseEvent): void {
  // Clear connection timeout
  if (connectionTimeout) {
    clearTimeout(connectionTimeout);
    connectionTimeout = null;
  }
  console.log(`[WS] Closed: code=${event.code}, reason=${event.reason}`);
  ws = null;
  useStore.getState().setConnected(false);

  // Notify VS Code extension of connection status
  postMessage({ type: 'connectionStatus', isConnected: false });

  if (!isIntentionallyClosed) {
    scheduleReconnect();
  }
}

function handleError(event: Event): void {
  console.error('[WS] Error:', event);
  // Note: The close event usually follows an error event, so reconnection
  // will be handled by handleClose. However, if the WebSocket is still in
  // CONNECTING state after an error (edge case), the connection timeout
  // will handle cleanup and reconnection.
}

function updateAtopileConfig(data: Record<string, unknown>): void {
  const update: Partial<AppState['atopile']> = {};

  // Actual installed atopile (source of truth)
  const actualVersion =
    (typeof data.actual_version === 'string' && data.actual_version) ||
    (typeof data.actualVersion === 'string' && data.actualVersion) ||
    null;
  if (actualVersion !== null) {
    update.actualVersion = actualVersion;
    // When we receive actualVersion, the server has started - clear installing state
    update.isInstalling = false;
    update.installProgress = null;
  }

  const actualSource =
    (typeof data.actual_source === 'string' && data.actual_source) ||
    (typeof data.actualSource === 'string' && data.actualSource) ||
    null;
  if (actualSource !== null) {
    update.actualSource = actualSource;
  }

  const actualBinaryPath =
    (typeof data.actual_binary_path === 'string' && data.actual_binary_path) ||
    (typeof data.actualBinaryPath === 'string' && data.actualBinaryPath) ||
    null;
  if (actualBinaryPath !== null) {
    update.actualBinaryPath = actualBinaryPath;
  }

  console.log('[WS] updateAtopileConfig received:', {
    actualVersion,
    actualSource,
    actualBinaryPath,
    source: data.source,
    localPath: data.local_path || data.localPath,
  });

  // User's selection in the dropdown
  if (typeof data.source === 'string') {
    update.source = data.source as AppState['atopile']['source'];
  }

  const currentVersion =
    (typeof data.current_version === 'string' && data.current_version) ||
    (typeof data.currentVersion === 'string' && data.currentVersion) ||
    null;
  if (currentVersion !== null) {
    update.currentVersion = currentVersion;
  }

  if (typeof data.branch === 'string') {
    update.branch = data.branch;
  }

  const localPath =
    (typeof data.local_path === 'string' && data.local_path) ||
    (typeof data.localPath === 'string' && data.localPath) ||
    null;
  if (localPath !== null) {
    update.localPath = localPath;
  }

  if (Array.isArray(data.available_versions)) {
    update.availableVersions = data.available_versions as string[];
  } else if (Array.isArray(data.availableVersions)) {
    update.availableVersions = data.availableVersions as string[];
  }

  if (Array.isArray(data.available_branches)) {
    update.availableBranches = data.available_branches as string[];
  } else if (Array.isArray(data.availableBranches)) {
    update.availableBranches = data.availableBranches as string[];
  }

  if (Array.isArray(data.detected_installations)) {
    update.detectedInstallations =
      data.detected_installations as AppState['atopile']['detectedInstallations'];
  } else if (Array.isArray(data.detectedInstallations)) {
    update.detectedInstallations =
      data.detectedInstallations as AppState['atopile']['detectedInstallations'];
  }

  if (typeof data.is_installing === 'boolean') {
    update.isInstalling = data.is_installing as boolean;
  } else if (typeof data.isInstalling === 'boolean') {
    update.isInstalling = data.isInstalling as boolean;
  }

  if (data.install_progress && typeof data.install_progress === 'object') {
    update.installProgress =
      data.install_progress as AppState['atopile']['installProgress'];
  } else if (data.installProgress && typeof data.installProgress === 'object') {
    update.installProgress =
      data.installProgress as AppState['atopile']['installProgress'];
  }

  if (typeof data.error === 'string') {
    update.error = data.error;
  }

  if (Object.keys(update).length > 0) {
    useStore.getState().setAtopileConfig(update);
    // NOTE: Don't forward backend state to VS Code settings here.
    // Settings are only saved when the user explicitly changes them in SidebarHeader.
    // The backend state is informational (what's currently running), not the user's preference.
  }
}

function scheduleReconnect(): void {
  if (isIntentionallyClosed) return;

  // Don't schedule if already scheduled
  if (reconnectTimeout) {
    console.log('[WS] Reconnect already scheduled');
    return;
  }

  // Calculate delay with exponential backoff
  const delay = Math.min(
    RECONNECT_DELAY_MS * Math.pow(RECONNECT_BACKOFF_MULTIPLIER, reconnectAttempts),
    MAX_RECONNECT_DELAY_MS
  );

  console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1})`);

  reconnectTimeout = setTimeout(() => {
    reconnectTimeout = null; // Clear before calling connect
    reconnectAttempts++;
    connect();
  }, delay);
}

// Export for use in components
export default {
  connect,
  disconnect,
  sendAction,
  isConnected,
};
