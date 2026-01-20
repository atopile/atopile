/**
 * Development Server for webview UI.
 *
 * Thin bridge that provides AppState over WebSocket for browser-based development.
 * Fetches data from the Python dashboard API (single source of truth).
 *
 * Usage:
 *   npx tsx server/dev-server.ts [workspace_paths...]
 *
 * Example:
 *   npx tsx server/dev-server.ts /Users/me/projects/atopile /Users/me/projects/packages
 */

import { WebSocketServer, WebSocket } from 'ws';
import * as http from 'http';
import * as fs from 'fs';
import * as path from 'path';

const DEV_SERVER_PORT = 3001;
const DASHBOARD_URL = 'http://localhost:8501';
const HTTP_SERVER_PORT = 3002; // For serving viewer pages

// Types matching AppState
interface AppState {
  isConnected: boolean;
  projects: Project[];
  selectedProjectRoot: string | null;
  selectedTargetNames: string[];
  builds: Build[];
  // Packages
  packages: PackageInfo[];
  isLoadingPackages: boolean;
  // Registry search
  registryResults: PackageInfo[];
  isSearchingRegistry: boolean;
  registrySearchQuery: string;
  selectedBuildName: string | null;
  selectedProjectName: string | null;
  selectedStageIds: string[];
  logEntries: LogEntry[];
  isLoadingLogs: boolean;
  logFile: string | null;
  enabledLogLevels: LogLevel[];
  logSearchQuery: string;
  logTimestampMode: 'absolute' | 'delta';
  logAutoScroll: boolean;
  // Log counts (from /api/logs/counts for efficient badge display)
  logCounts: {
    DEBUG: number;
    INFO: number;
    WARNING: number;
    ERROR: number;
    ALERT: number;
  };
  logTotalCount: number;
  logHasMore: boolean;
  expandedTargets: string[];
  version: string;
  logoUri: string;
  // Atopile configuration
  atopile: {
    currentVersion: string;
    source: 'release' | 'branch' | 'local';
    localPath: string | null;
    branch: string | null;
    availableVersions: string[];
    availableBranches: string[];
    detectedInstallations: {
      path: string;
      version: string | null;
      source: 'path' | 'venv' | 'manual';
    }[];
    isInstalling: boolean;
    installProgress: { message: string; percent?: number } | null;
    error: string | null;
  };
  // Standard library
  stdlibItems: StdLibItem[];
  isLoadingStdlib: boolean;
  // BOM (Bill of Materials)
  bomData: BOMData | null;
  isLoadingBOM: boolean;
  bomError: string | null;
  // Package details (for detail panel)
  selectedPackageDetails: PackageDetails | null;
  isLoadingPackageDetails: boolean;
  packageDetailsError: string | null;
  // Problems (errors/warnings)
  problems: Problem[];
  isLoadingProblems: boolean;
}

interface Project {
  root: string;
  name: string;
  targets: BuildTarget[];
}

interface BuildTarget {
  name: string;
  entry: string;
  root: string;
}

interface Build {
  name: string;
  display_name: string;
  project_name: string | null;
  status: 'queued' | 'building' | 'success' | 'warning' | 'failed';
  elapsed_seconds: number;
  warnings: number;
  errors: number;
  return_code: number | null;
  log_dir?: string;
  log_file?: string;
  stages?: BuildStage[];
  target_names?: string[];  // For matching active builds to targets
  build_id?: string;  // For cancel functionality
}

interface BuildStage {
  name: string;
  stage_id: string;
  display_name?: string;  // User-friendly name
  elapsed_seconds: number;
  status: 'pending' | 'running' | 'success' | 'warning' | 'failed' | 'error' | 'skipped';
  infos: number;
  warnings: number;
  errors: number;
  alerts: number;
}

// Live build status from /api/build/{id}/status
interface LiveBuildStatus {
  build_id: string;
  status: string;
  project_root: string;
  targets: string[];
  return_code: number | null;
  error: string | null;
  elapsed_seconds: number | null;
  current_stage: string | null;
  stages: {
    name: string;
    display_name: string;
    status: string;
    elapsed_seconds: number | null;
  }[];
}

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  logger: string;
  stage: string;
  message: string;
  ato_traceback?: string;
  exc_info?: string;
}

type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'ALERT';

// Problem types (errors/warnings from builds)
interface Problem {
  id: string;
  level: 'error' | 'warning';
  message: string;
  file?: string;
  line?: number;
  column?: number;
  stage?: string;
  logger?: string;
  buildName?: string;
  projectName?: string;
  timestamp?: string;
  ato_traceback?: string;
}

// Backend API response types (snake_case)
interface BackendProblem {
  level: string;
  message: string;
  file?: string | null;
  line?: number | null;
  column?: number | null;
  stage?: string | null;
  logger?: string | null;
  build_name?: string | null;
  project_name?: string | null;
  timestamp?: string | null;
  ato_traceback?: string | null;
}

interface ProblemsResponse {
  problems: BackendProblem[];
  total: number;
  error_count: number;
  warning_count: number;
}

// API Response types
interface ProjectsResponse {
  projects: Project[];
  total: number;
}

interface BuildSummaryResponse {
  builds: Build[];
  totals?: {
    builds: number;
    successful: number;
    failed: number;
    warnings: number;
    errors: number;
  };
}

// Standard Library types
type StdLibItemType = 'interface' | 'module' | 'component' | 'trait' | 'parameter';

interface StdLibChild {
  name: string;
  type: string;
  item_type: StdLibItemType;
  children: StdLibChild[];
}

interface StdLibItem {
  id: string;
  name: string;
  type: StdLibItemType;
  description: string;
  usage: string | null;
  children: StdLibChild[];
  parameters: { name: string; type: string }[];
}

interface StdLibResponse {
  items: StdLibItem[];
  total: number;
}

// Package types
interface PackageInfo {
  identifier: string;
  name: string;
  publisher: string;
  version?: string;
  latest_version?: string;
  description?: string;
  summary?: string;
  homepage?: string;
  repository?: string;
  license?: string;
  installed: boolean;
  installed_in: string[];
  // Stats from registry (may be null if not fetched)
  downloads?: number;
  version_count?: number;
  keywords?: string[];
}

interface PackagesResponse {
  packages: PackageInfo[];
  total: number;
}

interface RegistrySearchResponse {
  packages: PackageInfo[];
  total: number;
  query: string;
}

// Package version/release info
interface PackageVersion {
  version: string;
  released_at: string | null;
  requires_atopile?: string;
  size?: number;
}

// Detailed package info from registry
interface PackageDetails {
  identifier: string;
  name: string;
  publisher: string;
  version: string;  // Latest version
  summary?: string;
  description?: string;
  homepage?: string;
  repository?: string;
  license?: string;
  // Stats
  downloads?: number;
  downloads_this_week?: number;
  downloads_this_month?: number;
  // Versions
  versions: PackageVersion[];
  version_count: number;
  // Installation status
  installed: boolean;
  installed_version?: string;
  installed_in: string[];
}

// BOM types
type BOMComponentType =
  | 'resistor' | 'capacitor' | 'inductor' | 'ic' | 'connector'
  | 'led' | 'diode' | 'transistor' | 'crystal' | 'other';

interface BOMParameter {
  name: string;
  value: string;
  unit?: string;
}

interface BOMUsage {
  address: string;
  designator: string;
}

interface BOMComponent {
  id: string;
  lcsc?: string;
  manufacturer?: string;
  mpn?: string;
  type: BOMComponentType;
  value: string;
  package: string;
  description?: string;
  quantity: number;
  unitCost?: number;
  stock?: number;
  isBasic?: boolean;
  isPreferred?: boolean;
  source: string;
  parameters: BOMParameter[];
  usages: BOMUsage[];
}

interface BOMData {
  version: string;
  components: BOMComponent[];
}

/**
 * Watches a log file for changes and streams new entries.
 */
class LogFileWatcher {
  private watcher: fs.FSWatcher | null = null;
  private filePath: string;
  private lastPosition: number = 0;
  private onNewEntries: (entries: LogEntry[]) => void;
  private debounceTimer: NodeJS.Timeout | null = null;

  constructor(filePath: string, onNewEntries: (entries: LogEntry[]) => void) {
    this.filePath = filePath;
    this.onNewEntries = onNewEntries;
  }

  async start(): Promise<LogEntry[]> {
    const entries = await this.readAllEntries();

    try {
      this.watcher = fs.watch(this.filePath, { persistent: false }, (eventType) => {
        if (eventType === 'change') {
          this.handleFileChange();
        }
      });
    } catch (error) {
      console.error(`Failed to watch log file: ${error}`);
    }

    return entries;
  }

  stop(): void {
    if (this.watcher) {
      this.watcher.close();
      this.watcher = null;
    }
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
  }

  private async readAllEntries(): Promise<LogEntry[]> {
    try {
      const content = await fs.promises.readFile(this.filePath, 'utf-8');
      this.lastPosition = Buffer.byteLength(content, 'utf-8');
      return this.parseEntries(content);
    } catch (error) {
      console.error(`Failed to read log file: ${error}`);
      return [];
    }
  }

  private handleFileChange(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    this.debounceTimer = setTimeout(() => {
      this.readNewEntries();
    }, 50);
  }

  private async readNewEntries(): Promise<void> {
    try {
      const stats = await fs.promises.stat(this.filePath);
      if (stats.size <= this.lastPosition) {
        return;
      }

      const fd = await fs.promises.open(this.filePath, 'r');
      const buffer = Buffer.alloc(stats.size - this.lastPosition);
      await fd.read(buffer, 0, buffer.length, this.lastPosition);
      await fd.close();

      this.lastPosition = stats.size;
      const newContent = buffer.toString('utf-8');
      const newEntries = this.parseEntries(newContent);

      if (newEntries.length > 0) {
        this.onNewEntries(newEntries);
      }
    } catch (error) {
      console.error(`Failed to read new log entries: ${error}`);
    }
  }

  private parseEntries(content: string): LogEntry[] {
    return content
      .split('\n')
      .filter(line => line.trim())
      .map(line => {
        try {
          return JSON.parse(line) as LogEntry;
        } catch {
          return {
            timestamp: new Date().toISOString(),
            level: 'INFO' as const,
            logger: 'unknown',
            stage: 'unknown',
            message: line,
          };
        }
      });
  }
}

// Helper to deep compare values for state diffing
function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== typeof b) return false;
  if (a === null || b === null) return a === b;
  if (typeof a !== 'object') return false;

  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    return a.every((item, i) => deepEqual(item, b[i]));
  }

  if (Array.isArray(a) || Array.isArray(b)) return false;

  const aObj = a as Record<string, unknown>;
  const bObj = b as Record<string, unknown>;
  const aKeys = Object.keys(aObj);
  const bKeys = Object.keys(bObj);

  if (aKeys.length !== bKeys.length) return false;
  return aKeys.every(key => deepEqual(aObj[key], bObj[key]));
}

class DevServer {
  private state: AppState;
  private lastBroadcastState: Partial<AppState> = {}; // Track what we last sent
  private clients: Set<WebSocket> = new Set();
  private wss: WebSocketServer | null = null;
  private httpServer: http.Server | null = null;
  private pollInterval: NodeJS.Timeout | null = null;
  private workspacePaths: string[];
  private logPollTimer: NodeJS.Timeout | null = null;  // For polling logs via API
  private lastLogId: number = 0;  // For cursor-based log pagination
  private searchDebounceTimer: NodeJS.Timeout | null = null;  // For debouncing search
  private lastSearchQuery: string = '';
  private pendingUpdates: Set<keyof AppState> = new Set(); // Track which fields need broadcast
  private updateTimeout: NodeJS.Timeout | null = null; // Debounce updates
  
  // Backend WebSocket connection for event-driven updates
  private backendSocket: WebSocket | null = null;
  private backendReconnectTimer: NodeJS.Timeout | null = null;

  constructor(workspacePaths: string[]) {
    this.workspacePaths = workspacePaths;
    this.state = this.createInitialState();
  }

  async start(port: number = DEV_SERVER_PORT): Promise<void> {
    // Start HTTP server for viewer pages
    this.startHttpServer();

    this.wss = new WebSocketServer({ port });

    this.wss.on('connection', (ws) => {
      console.log('Client connected');
      this.clients.add(ws);

      // Send current state immediately
      this.sendStateTo(ws);

      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          if (message.type === 'ready') {
            this.sendStateTo(ws);
          } else if (message.type === 'action') {
            this.handleAction(message);
          } else if (message.type === 'perf') {
            this.logPerf(message);
          }
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      });

      ws.on('close', () => {
        console.log('Client disconnected');
        this.clients.delete(ws);
      });
    });

    console.log(`Dev Server listening on ws://localhost:${port}`);

    // Connect to backend WebSocket for real-time events
    this.connectToBackend();

    // Initial fetch (one-time, not polling)
    await this.fetchAll();
  }

  /**
   * Connect to the Python backend WebSocket for real-time events.
   */
  private connectToBackend(): void {
    // Derive WebSocket URL from DASHBOARD_URL (replace http with ws)
    const wsUrl = DASHBOARD_URL.replace('http://', 'ws://') + '/ws/events';
    console.log(`Connecting to backend WebSocket: ${wsUrl}`);

    try {
      this.backendSocket = new WebSocket(wsUrl);

      this.backendSocket.on('open', () => {
        console.log('Connected to backend WebSocket');
        // Clear any reconnect timer
        if (this.backendReconnectTimer) {
          clearTimeout(this.backendReconnectTimer);
          this.backendReconnectTimer = null;
        }
        // Subscribe to all channels
        this.subscribeToBackendChannels();
      });

      this.backendSocket.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleBackendEvent(message);
        } catch (e) {
          console.error('Failed to parse backend message:', e);
        }
      });

      this.backendSocket.on('close', () => {
        console.log('Backend WebSocket closed, reconnecting in 2s...');
        this.scheduleBackendReconnect();
      });

      this.backendSocket.on('error', (error) => {
        console.error('Backend WebSocket error:', error.message);
        // Will trigger close event, which handles reconnection
      });

    } catch (e) {
      console.error('Failed to connect to backend:', e);
      this.scheduleBackendReconnect();
    }
  }

  /**
   * Schedule a reconnection to the backend.
   */
  private scheduleBackendReconnect(): void {
    if (this.backendReconnectTimer) return;
    this.backendReconnectTimer = setTimeout(() => {
      this.backendReconnectTimer = null;
      this.connectToBackend();
    }, 2000);
  }

  /**
   * Subscribe to backend event channels.
   */
  private subscribeToBackendChannels(): void {
    if (!this.backendSocket || this.backendSocket.readyState !== WebSocket.OPEN) return;

    // Subscribe to builds channel
    this.sendToBackend({ action: 'subscribe', channel: 'builds' });

    // Subscribe to summary channel
    this.sendToBackend({ action: 'subscribe', channel: 'summary' });

    // Subscribe to problems channel
    this.sendToBackend({ action: 'subscribe', channel: 'problems' });

    // Subscribe to logs channel with current filter
    this.updateLogSubscription();
  }

  /**
   * Send a message to the backend WebSocket.
   */
  private sendToBackend(message: object): void {
    if (this.backendSocket && this.backendSocket.readyState === WebSocket.OPEN) {
      this.backendSocket.send(JSON.stringify(message));
    }
  }

  /**
   * Update log subscription with current filter state.
   */
  private updateLogSubscription(): void {
    const filters: Record<string, any> = {
      limit: 100,
    };

    if (this.state.selectedBuildName) {
      filters.build_name = this.state.selectedBuildName;
    }
    if (this.state.selectedProjectName) {
      filters.project_name = this.state.selectedProjectName;
    }
    // Use enabledLogLevels - only send if not all levels enabled
    if (this.state.enabledLogLevels && this.state.enabledLogLevels.length > 0 && this.state.enabledLogLevels.length < 5) {
      filters.levels = this.state.enabledLogLevels;
    }
    if (this.state.logSearchQuery) {
      filters.search = this.state.logSearchQuery;
    }

    console.log('Updating log subscription with filters:', filters);
    this.sendToBackend({
      action: 'update_filter',
      channel: 'logs',
      filters,
    });
  }

  /**
   * Handle an event received from the backend WebSocket.
   */
  private handleBackendEvent(message: { event: string; data: any }): void {
    const { event, data } = message;
    console.log('Backend event:', event);

    switch (event) {
      case 'logs':
        this.handleLogsEvent(data);
        break;

      case 'build:started':
        this.handleBuildStartedEvent(data);
        break;

      case 'build:stage':
        this.handleBuildStageEvent(data);
        break;

      case 'build:completed':
        this.handleBuildCompletedEvent(data);
        break;

      case 'summary:updated':
        // Re-fetch summary data
        this.fetchBuilds();
        break;

      case 'problems:updated':
        // Re-fetch problems data
        this.fetchProblems();
        break;

      default:
        console.log('Unknown backend event:', event);
    }
  }

  /**
   * Handle logs data from backend.
   */
  private handleLogsEvent(data: { logs: any[]; total?: number; incremental?: boolean }): void {
    // Map backend log format to LogEntry format
    const mapToLogEntry = (log: any): LogEntry => ({
      timestamp: log.timestamp || new Date().toISOString(),
      level: (log.level || 'INFO').toUpperCase() as LogLevel,
      logger: log.logger || log.stage || 'build',
      stage: log.stage || 'build',
      message: log.message || '',
      ato_traceback: log.ato_traceback,
      exc_info: log.exc_info,
    });

    if (data.incremental) {
      // Append new logs to the beginning (newest first)
      const newLogs = data.logs.map(mapToLogEntry);
      // Avoid duplicates based on timestamp and message
      const filtered = newLogs.filter(
        (log) => !this.state.logEntries.some(
          (existing) => existing.timestamp === log.timestamp && existing.message === log.message
        )
      );
      if (filtered.length > 0) {
        this.state.logEntries = [...filtered, ...this.state.logEntries];
        this.queueUpdate('logEntries');
      }
    } else {
      // Full replacement
      this.state.logEntries = (data.logs || []).map(mapToLogEntry);
      if (data.total !== undefined) {
        this.state.logTotalCount = data.total;
      }
      this.state.isLoadingLogs = false;
      this.queueUpdate('logEntries', 'logTotalCount', 'isLoadingLogs');
    }
  }

  /**
   * Handle build:started event.
   */
  private handleBuildStartedEvent(data: {
    build_id: string;
    project_root: string;
    targets: string[];
    stages: any[];
  }): void {
    console.log(`Build started: ${data.build_id}`);

    const projectName = this.extractProjectName(data.project_root);
    const targetNames = data.targets.length > 0 ? data.targets : ['default'];

    // Create a new Build entry for this active build
    const newBuild: Build = {
      name: `${projectName}:${targetNames[0]}`,
      display_name: `${projectName} / ${targetNames[0]}`,
      project_name: projectName,
      status: 'building',
      elapsed_seconds: 0,
      warnings: 0,
      errors: 0,
      return_code: null,
      build_id: data.build_id,
      target_names: targetNames,
      stages: data.stages.map((s) => ({
        name: s.name,
        stage_id: s.name,
        display_name: s.display_name || s.name,
        elapsed_seconds: s.elapsed_seconds || 0,
        status: (s.status || 'pending') as BuildStage['status'],
        infos: 0,
        warnings: 0,
        errors: 0,
        alerts: 0,
      })),
    };

    // Check if this build already exists, update it; otherwise add
    const existingIdx = this.state.builds.findIndex(
      (b) => b.build_id === data.build_id || 
             (b.name === newBuild.name && b.status === 'building')
    );
    
    if (existingIdx >= 0) {
      this.state.builds[existingIdx] = newBuild;
    } else {
      this.state.builds = [newBuild, ...this.state.builds];
    }

    this.queueUpdate('builds');
  }

  /**
   * Handle build:stage event.
   */
  private handleBuildStageEvent(data: {
    build_id: string;
    stage_name: string;
    display_name: string;
    status: string;
    stage_index?: number;
    project_root?: string;
  }): void {
    console.log(`Build stage: ${data.stage_name} -> ${data.status}`);

    // Find and update the build
    this.state.builds = this.state.builds.map((build) => {
      if (build.build_id === data.build_id) {
        return {
          ...build,
          stages: build.stages?.map((stage, idx) => {
            if (stage.name === data.stage_name || idx === data.stage_index) {
              return {
                ...stage,
                status: data.status as BuildStage['status'],
              };
            }
            // Mark previous stages as success if they were pending
            if (data.stage_index !== undefined && idx < data.stage_index && stage.status === 'pending') {
              return { ...stage, status: 'success' as const };
            }
            return stage;
          }),
        };
      }
      return build;
    });

    this.queueUpdate('builds');
  }

  /**
   * Handle build:completed event.
   */
  private handleBuildCompletedEvent(data: {
    build_id: string;
    project_root: string;
    targets: string[];
    status: string;
    return_code: number;
    stages?: any[];
    error?: string;
  }): void {
    console.log(`Build completed: ${data.build_id} -> ${data.status}`);

    // Map status to Build status type
    const finalStatus: Build['status'] = 
      data.status === 'success' ? 'success' :
      data.status === 'warning' ? 'warning' : 'failed';

    // Find and update the build
    this.state.builds = this.state.builds.map((build) => {
      if (build.build_id === data.build_id) {
        return {
          ...build,
          status: finalStatus,
          return_code: data.return_code,
          stages: data.stages?.map((s) => ({
            name: s.name,
            stage_id: s.name,
            display_name: s.display_name || s.name,
            elapsed_seconds: s.elapsed_seconds || 0,
            status: s.status as BuildStage['status'],
            infos: 0,
            warnings: 0,
            errors: 0,
            alerts: 0,
          })) || build.stages,
        };
      }
      return build;
    });

    this.queueUpdate('builds');

    // Fetch fresh summary to get final build details
    setTimeout(() => this.fetchBuilds(), 500);
  }

  /**
   * Extract project name from project root path.
   */
  private extractProjectName(projectRoot: string): string {
    const parts = projectRoot.split('/');
    return parts[parts.length - 1] || projectRoot;
  }

  // Performance logging from webview
  private logPerf(message: any): void {
    const { name, duration, metadata } = message;
    const rating = duration < 16 ? 'FAST' : duration < 50 ? 'GOOD' : duration < 100 ? 'OK' : duration < 200 ? 'SLOW' : 'CRITICAL';
    const color = duration < 16 ? '\x1b[32m' : duration < 50 ? '\x1b[36m' : duration < 100 ? '\x1b[33m' : duration < 200 ? '\x1b[35m' : '\x1b[31m';
    const reset = '\x1b[0m';
    const dim = '\x1b[2m';
    const bold = '\x1b[1m';
    const ms = duration < 1 ? `${(duration * 1000).toFixed(0)}µs` : `${duration.toFixed(2)}ms`;
    const meta = metadata ? ` ${dim}${JSON.stringify(metadata)}${reset}` : '';
    console.log(`${dim}[PERF]${reset} ${color}${bold}${rating}${reset} ${name}: ${color}${ms}${reset}${meta}`);
  }

  private async handleAction(message: any): Promise<void> {
    console.log('Action:', message.action, message);

    switch (message.action) {
      case 'selectProject':
        this.state.selectedProjectRoot = message.root;
        const project = this.state.projects.find(p => p.root === message.root);
        this.state.selectedTargetNames = project?.targets.map(t => t.name) || [];
        this.queueUpdate('selectedProjectRoot', 'selectedTargetNames');
        // Fetch BOM for the newly selected project
        await this.fetchBOM(message.root, 'default');
        return; // fetchBOM handles its own broadcast

      case 'toggleTarget':
        const idx = this.state.selectedTargetNames.indexOf(message.name);
        if (idx >= 0) {
          this.state.selectedTargetNames = this.state.selectedTargetNames.filter(n => n !== message.name);
        } else {
          this.state.selectedTargetNames = [...this.state.selectedTargetNames, message.name];
        }
        this.queueUpdate('selectedTargetNames');
        return;

      case 'toggleTargetExpanded':
        const expIdx = this.state.expandedTargets.indexOf(message.name);
        if (expIdx >= 0) {
          this.state.expandedTargets = this.state.expandedTargets.filter(n => n !== message.name);
        } else {
          this.state.expandedTargets = [...this.state.expandedTargets, message.name];
        }
        this.queueUpdate('expandedTargets');
        return;

      case 'selectBuild':
        await this.selectBuild(message.buildName, message.projectName);
        break;

      case 'toggleStageFilter':
        const stageIdx = this.state.selectedStageIds.indexOf(message.stageId);
        if (stageIdx >= 0) {
          this.state.selectedStageIds = this.state.selectedStageIds.filter(id => id !== message.stageId);
        } else {
          this.state.selectedStageIds = [...this.state.selectedStageIds, message.stageId];
        }
        this.queueUpdate('selectedStageIds');
        // Trigger server refresh with new stage filter
        this.triggerLogRefresh();
        return;

      case 'toggleLogLevel':
        const levelIdx = this.state.enabledLogLevels.indexOf(message.level);
        if (levelIdx >= 0) {
          this.state.enabledLogLevels = this.state.enabledLogLevels.filter(l => l !== message.level);
        } else {
          this.state.enabledLogLevels = [...this.state.enabledLogLevels, message.level];
        }
        this.queueUpdate('enabledLogLevels');
        // Trigger server refresh with new level filter
        this.triggerLogRefresh();
        return;

      case 'setLogSearchQuery':
        this.state.logSearchQuery = message.query || '';
        this.queueUpdate('logSearchQuery');
        // Debounce search queries before triggering server refresh
        if (this.searchDebounceTimer) {
          clearTimeout(this.searchDebounceTimer);
        }
        if (message.query !== this.lastSearchQuery) {
          this.searchDebounceTimer = setTimeout(() => {
            this.lastSearchQuery = message.query || '';
            this.triggerLogRefresh();
          }, 300);  // 300ms debounce
        }
        return;

      case 'setLogTimestampMode':
        this.state.logTimestampMode = message.mode;
        this.queueUpdate('logTimestampMode');
        return;

      case 'toggleLogTimestampMode':
        this.state.logTimestampMode = this.state.logTimestampMode === 'absolute' ? 'delta' : 'absolute';
        this.queueUpdate('logTimestampMode');
        return;

      case 'setLogAutoScroll':
        this.state.logAutoScroll = message.enabled;
        this.queueUpdate('logAutoScroll');
        return;

      case 'build':
        console.log('Build requested for:', this.state.selectedTargetNames);
        await this.triggerBuild(message);
        break;

      case 'refreshProjects':
        console.log('Refreshing projects from backend...');
        await this.fetchProjects();
        break;

      case 'refreshStdlib':
        console.log('Refreshing standard library from backend...');
        await this.fetchStdlib();
        break;

      case 'refreshPackages':
        console.log('Refreshing packages from backend...');
        await this.fetchPackages();
        break;

      case 'installPackage':
        console.log('Installing package:', message.packageId, 'to', message.projectRoot);
        await this.installPackage(message.packageId, message.projectRoot, message.version);
        break;

      case 'removePackage':
        console.log('Removing package:', message.packageId, 'from', message.projectRoot);
        await this.removePackage(message.packageId, message.projectRoot);
        break;

      case 'searchRegistry':
        console.log('Searching registry for:', message.query);
        await this.searchRegistry(message.query);
        break;

      case 'clearRegistrySearch':
        this.state.registryResults = [];
        this.state.registrySearchQuery = '';
        this.state.isSearchingRegistry = false;
        this.queueUpdate('registryResults', 'registrySearchQuery', 'isSearchingRegistry');
        return;

      case 'refreshBOM':
        console.log('Refreshing BOM for:', message.projectRoot, 'target:', message.target);
        await this.fetchBOM(message.projectRoot, message.target || 'default');
        break;

      case 'clearBOM':
        this.state.bomData = null;
        this.state.bomError = null;
        this.queueUpdate('bomData', 'bomError');
        return;

      case 'refreshProblems':
        console.log('Refreshing problems for:', message.projectRoot, 'build:', message.buildName);
        await this.fetchProblems(message.projectRoot, message.buildName);
        break;

      case 'getPackageDetails':
        console.log('Fetching package details for:', message.packageId);
        await this.fetchPackageDetails(message.packageId);
        break;

      case 'clearPackageDetails':
        this.state.selectedPackageDetails = null;
        this.state.packageDetailsError = null;
        this.queueUpdate('selectedPackageDetails', 'packageDetailsError');
        return;

      case 'buildPackage':
        console.log('Building package:', message.packageId, 'installing to:', message.projectRoot);
        await this.buildPackage(message.packageId, message.projectRoot, message.entry);
        break;

      case 'cancelBuild':
        console.log('Cancelling build:', message.buildId);
        await this.cancelBuild(message.buildId);
        break;

      case 'openFile':
        await this.handleOpenFile(message);
        break;

      case 'openSource':
        await this.handleOpenSource(message.projectId, message.entry);
        break;

      case 'openKiCad':
        await this.handleOpenKiCad(message.projectId, message.buildId);
        break;

      case 'openLayout':
        await this.handleOpenLayout(message.projectId, message.buildId);
        break;

      case 'open3D':
        await this.handleOpen3D(message.projectId, message.buildId);
        break;

      case 'createProject':
        console.log('Creating project in:', message.parentDirectory, 'name:', message.name);
        await this.createProject(message.parentDirectory, message.name);
        break;

      case 'renameProject':
        console.log('Renaming project:', message.projectRoot, 'to:', message.newName);
        await this.renameProject(message.projectRoot, message.newName);
        break;

      // Atopile version management
      case 'setAtopileVersion':
        console.log('Setting atopile version:', message.version);
        await this.setAtopileVersion(message.version);
        break;

      case 'setAtopileSource':
        console.log('Setting atopile source:', message.source);
        this.state.atopile.source = message.source;
        // If switching to branch, trigger branch install
        if (message.source === 'branch' && this.state.atopile.branch) {
          this.setAtopieBranch(this.state.atopile.branch);
        }
        break;

      case 'setAtopileLocalPath':
        console.log('Setting atopile local path:', message.path);
        this.state.atopile.localPath = message.path;
        break;

      case 'setAtopieBranch':
        console.log('Setting atopile branch:', message.branch);
        await this.setAtopieBranch(message.branch);
        break;

      case 'refreshAtopieBranches':
        console.log('Refreshing atopile branches from GitHub...');
        await this.fetchAtopieBranches();
        break;

      case 'browseAtopilePath':
        console.log('Browse for atopile path requested (would open file picker in extension)');
        // In real extension, this would open a file picker dialog
        break;

      case 'refreshAtopileVersions':
        console.log('Refreshing atopile versions from PyPI...');
        await this.fetchAtopileVersions();
        break;

      default:
        console.log('Unhandled action:', message.action);
    }

    this.broadcastState();
  }

  /**
   * Trigger a build via the Python backend.
   */
  private async triggerBuild(message: any): Promise<void> {
    let projectRoot: string | null = null;
    let targets: string[] = [];
    let entry: string | null = null;
    let standalone = false;

    console.log('triggerBuild called with:', JSON.stringify(message, null, 2));

    // Parse the build request based on level
    // level: 'project' | 'build' | 'symbol'
    // id: projectId or "projectId:buildId" or symbolPath
    if (message.level === 'project') {
      // Build entire project - id is the project root
      projectRoot = message.id;
      const project = this.state.projects.find(p => p.root === projectRoot);
      targets = project?.targets.map(t => t.name) || [];
      console.log('Project level build. projectRoot:', projectRoot, 'targets:', targets);
    } else if (message.level === 'build') {
      // Build specific target - id is "projectRoot:targetName"
      const parts = message.id.split(':');
      console.log('Build level. id:', message.id, 'parts:', parts);

      if (parts.length >= 2) {
        // Find the project by ID (which is the root path or project name)
        const projectIdOrName = parts.slice(0, -1).join(':');
        const targetName = parts[parts.length - 1];

        console.log('Looking for project:', projectIdOrName, 'target:', targetName);
        console.log('Available projects:', this.state.projects.map(p => ({ root: p.root, name: p.name })));

        // Try to find project by root or name
        const project = this.state.projects.find(p =>
          p.root === projectIdOrName || p.name === projectIdOrName
        );

        if (project) {
          projectRoot = project.root;
          targets = [targetName];
          console.log('Found project. projectRoot:', projectRoot, 'targets:', targets);
        } else {
          console.log('Project not found for:', projectIdOrName);
        }
      }
    } else if (message.level === 'symbol') {
      // Build specific symbol/entry point - use standalone mode
      // id format: "projectRoot:entry" where entry is "file.ato:Module"
      const parts = message.id.split(':');
      if (parts.length >= 3) {
        // Format: /path/to/project:file.ato:Module
        projectRoot = parts.slice(0, -2).join(':');
        entry = parts.slice(-2).join(':');  // "file.ato:Module"
        standalone = true;
        console.log('Symbol level build (standalone). projectRoot:', projectRoot, 'entry:', entry);
      }
    } else {
      // Fallback to selected project/targets
      projectRoot = message.projectRoot || this.state.selectedProjectRoot;
      targets = message.targets || this.state.selectedTargetNames;
      console.log('Fallback build. projectRoot:', projectRoot, 'targets:', targets);
    }

    if (!projectRoot) {
      console.log('No project selected for build');
      return;
    }

    if (targets.length === 0 && !standalone) {
      console.log('No targets specified for build and not standalone');
      return;
    }

    console.log(`Starting build for ${projectRoot} with targets:`, targets, 'standalone:', standalone, 'entry:', entry);

    // Update UI to show building state
    this.updateBuildStatus(projectRoot, targets.length > 0 ? targets : ['standalone'], 'building');

    try {
      const requestBody: any = {
        project_root: projectRoot,
        targets: targets,
        frozen: false,
      };

      // Add standalone build parameters if needed
      if (standalone && entry) {
        requestBody.standalone = true;
        requestBody.entry = entry;
      }

      const response = await this.httpPost(`${DASHBOARD_URL}/api/build`, requestBody);

      const result = JSON.parse(response);
      console.log('Build started:', result);
      // Build events will come via WebSocket - no polling needed
    } catch (e) {
      console.error('Failed to start build:', e);
      this.updateBuildStatus(projectRoot, targets.length > 0 ? targets : ['standalone'], 'failed');
    }
  }

  // NOTE: pollBuildStatus() removed - using WebSocket build:* events instead

  /**
   * Update the build status in the UI state.
   */
  private updateBuildStatus(
    projectRoot: string,
    targets: string[],
    status: string,
    buildInfo?: {
      buildId?: string;
      elapsedSeconds?: number;
      currentStage?: string | null;
      stages?: { name: string; display_name: string; status: string; elapsed_seconds: number | null }[];
    }
  ): void {
    const projectName = projectRoot.split('/').pop() || '';

    // First, try to find the build by build_id (for active builds)
    // This ensures we update the correct build entry, not an old completed one
    let existingBuild = buildInfo?.buildId
      ? this.state.builds.find(b => b.name === buildInfo.buildId || (b as any).build_id === buildInfo.buildId)
      : null;

    // If not found by build_id, create or update a synthetic build entry for this active build
    if (!existingBuild && buildInfo?.buildId) {
      // Create a new build entry for this active build
      const stages = buildInfo?.stages?.map(s => ({
        name: s.name,
        stage_id: s.name,
        display_name: s.display_name,
        elapsed_seconds: s.elapsed_seconds || 0,
        status: s.status as any,
        infos: 0,
        warnings: 0,
        errors: 0,
        alerts: 0,
      })) || [];

      const newBuild: Build = {
        name: buildInfo.buildId,
        display_name: `${projectName} (building)`,
        project_name: projectName,
        status: status as any,
        elapsed_seconds: buildInfo.elapsedSeconds || 0,
        warnings: 0,
        errors: 0,
        return_code: null,
        stages,
        target_names: targets,
        build_id: buildInfo.buildId,
      };
      this.state.builds.unshift(newBuild);
      this.queueUpdate('builds');
      return;
    }

    // Fall back to updating by target name (for legacy compatibility)
    for (const targetName of targets) {
      if (!existingBuild) {
        existingBuild = this.state.builds.find(
          b => b.name === targetName || b.display_name?.includes(targetName)
        );
      }

      if (existingBuild) {
        existingBuild.status = status as any;
        // Update target_names and build_id for matching in frontend
        if (targets.length > 0) {
          existingBuild.target_names = targets;
        }
        if (buildInfo) {
          if (buildInfo.buildId) {
            existingBuild.build_id = buildInfo.buildId;
          }
          existingBuild.elapsed_seconds = buildInfo.elapsedSeconds || existingBuild.elapsed_seconds;
          // Update stages in-place to avoid causing React re-renders
          if (buildInfo.stages && buildInfo.stages.length > 0) {
            // If we don't have stages yet, or the count differs, replace entirely
            if (!existingBuild.stages || existingBuild.stages.length !== buildInfo.stages.length) {
              existingBuild.stages = buildInfo.stages.map(s => ({
                name: s.name,
                stage_id: s.name,
                display_name: s.display_name,
                elapsed_seconds: s.elapsed_seconds || 0,
                status: s.status as any,
                infos: 0,
                warnings: 0,
                errors: 0,
                alerts: 0,
              }));
            } else {
              // Update stages in-place to preserve array reference
              for (let i = 0; i < buildInfo.stages.length; i++) {
                const newStage = buildInfo.stages[i];
                const existingStage = existingBuild.stages[i];
                if (existingStage) {
                  existingStage.status = newStage.status as any;
                  existingStage.elapsed_seconds = newStage.elapsed_seconds || 0;
                  existingStage.display_name = newStage.display_name;
                }
              }
            }
          }
        }
      } else {
        // Create a new build entry
        const stages = buildInfo?.stages?.map(s => ({
          name: s.name,
          stage_id: s.name,
          display_name: s.display_name,
          elapsed_seconds: s.elapsed_seconds || 0,
          status: s.status as any,
          infos: 0,
          warnings: 0,
          errors: 0,
          alerts: 0,
        })) || [];

        this.state.builds.push({
          name: buildInfo?.buildId || targetName,
          display_name: `${projectRoot.split('/').pop()}:${targetName}`,
          project_name: projectRoot.split('/').pop() || null,
          status: status as any,
          elapsed_seconds: buildInfo?.elapsedSeconds || 0,
          warnings: 0,
          errors: 0,
          return_code: null,
          stages: stages,
          target_names: [targetName],
          build_id: buildInfo?.buildId,
        });
      }
    }

    this.queueUpdate('builds');
  }

  /**
   * Select a build and load its logs via WebSocket subscription.
   */
  private async selectBuild(buildName: string | null, projectName: string | null = null): Promise<void> {
    // Check if selection actually changed
    if (this.state.selectedBuildName === buildName && this.state.selectedProjectName === projectName) {
      return;
    }

    this.state.selectedBuildName = buildName;
    this.state.selectedProjectName = projectName;
    this.state.selectedStageIds = [];
    this.state.logEntries = [];
    this.state.logFile = null;
    this.lastLogId = 0;

    this.state.isLoadingLogs = true;

    // Set log file if a specific build is selected
    if (buildName) {
      const build = this.state.builds.find(
        b => b.display_name === buildName || b.name === buildName
      );
      if (build) {
        this.state.logFile = build.log_file || null;
      }
    }

    this.queueUpdate('selectedBuildName', 'selectedProjectName', 'selectedStageIds', 'logEntries', 'logFile', 'isLoadingLogs');

    // Update WebSocket subscription with new filter
    this.updateLogSubscription();
  }

  /**
   * Fetch logs from the backend API with server-side filtering.
   */
  private async fetchLogs(buildName: string | null, projectName: string | null = null, incremental: boolean = false): Promise<void> {
    try {
      // Build query params with current filter state
      const params = new URLSearchParams();
      if (buildName) {
        params.set('build_name', buildName);
      }
      if (projectName) {
        params.set('project_name', projectName);
      }
      params.set('limit', '500');

      // Pass enabled levels to server (if not all levels enabled)
      if (this.state.enabledLogLevels.length > 0 && this.state.enabledLogLevels.length < 5) {
        params.set('levels', this.state.enabledLogLevels.join(','));
      }

      // Pass stage filter if set
      if (this.state.selectedStageIds.length > 0) {
        params.set('stage', this.state.selectedStageIds[0]);
      }

      // Pass search query
      if (this.state.logSearchQuery.trim()) {
        params.set('search', this.state.logSearchQuery.trim());
      }

      // For incremental polling, only fetch new logs
      if (incremental && this.lastLogId > 0) {
        params.set('after_id', String(this.lastLogId));
      }

      const response = await this.httpGet(`${DASHBOARD_URL}/api/logs/query?${params}`);
      const data = JSON.parse(response) as {
        logs?: Array<{
          id: number;
          timestamp: string;
          stage: string;
          level: string;
          message: string;
          ato_traceback: string | null;
          python_traceback: string | null;
        }>;
        total?: number;
        has_more?: boolean;
        max_id?: number;
        detail?: string;  // Error detail from API
      };

      // Handle API error responses
      if (!data.logs) {
        console.warn(`API returned no logs for ${buildName}: ${data.detail || 'unknown error'}`);
        this.state.isLoadingLogs = false;
        this.queueUpdate('isLoadingLogs');
        return;
      }

      // Convert API response to LogEntry format
      const newEntries: LogEntry[] = data.logs.map(log => ({
        timestamp: log.timestamp,
        level: log.level as LogLevel,
        logger: 'atopile',
        stage: log.stage,
        message: log.message,
        ato_traceback: log.ato_traceback ?? undefined,
        exc_info: log.python_traceback ?? undefined,
      }));

      // For incremental updates, append; otherwise replace
      if (incremental && this.lastLogId > 0 && newEntries.length > 0) {
        // Append new entries (they're in ASC order when using after_id)
        this.state.logEntries = [...this.state.logEntries, ...newEntries];
      } else if (!incremental) {
        // Full refresh - reverse to get chronological order
        this.state.logEntries = newEntries.reverse();
      }

      // Update tracking
      this.lastLogId = data.max_id || this.lastLogId;
      this.state.logTotalCount = data.total ?? newEntries.length;
      this.state.logHasMore = data.has_more ?? false;
      this.state.isLoadingLogs = false;

      this.queueUpdate('logEntries', 'isLoadingLogs', 'logTotalCount', 'logHasMore');
      console.log(`Fetched ${newEntries.length} log entries for ${buildName} (total: ${data.total ?? 'unknown'}, incremental: ${incremental})`);
    } catch (error) {
      console.error(`Failed to fetch logs: ${error}`);
      this.state.isLoadingLogs = false;
      this.queueUpdate('isLoadingLogs');
    }
  }

  /**
   * Fetch log counts by level for UI badges.
   */
  private async fetchLogCounts(buildName: string | null, projectName: string | null = null): Promise<void> {
    try {
      const params = new URLSearchParams();
      if (buildName) {
        params.set('build_name', buildName);
      }
      if (projectName) {
        params.set('project_name', projectName);
      }

      // Pass stage filter if set
      if (this.state.selectedStageIds.length > 0) {
        params.set('stage', this.state.selectedStageIds[0]);
      }

      const response = await this.httpGet(`${DASHBOARD_URL}/api/logs/counts?${params}`);
      const data = JSON.parse(response) as {
        counts: { DEBUG: number; INFO: number; WARNING: number; ERROR: number; ALERT: number };
        total: number;
      };

      this.state.logCounts = data.counts;
      // Don't emit separately - will be batched with log fetch
    } catch (error) {
      console.error(`Failed to fetch log counts: ${error}`);
    }
  }

  // NOTE: startPollingLogs() and stopPollingLogs() removed - using WebSocket subscription instead

  /**
   * Trigger a log refresh when filters change.
   * Updates the WebSocket subscription to get new filtered data.
   */
  private triggerLogRefresh(): void {
    this.lastLogId = 0;
    this.state.isLoadingLogs = true;
    this.state.logEntries = [];  // Clear current logs
    this.queueUpdate('isLoadingLogs', 'logEntries');
    // Update WebSocket subscription - backend will send filtered logs
    this.updateLogSubscription();
  }

  // Maximum log entries to include in initial state (to avoid 2MB+ payloads)
  private static readonly MAX_INITIAL_LOG_ENTRIES = 500;

  private sendStateTo(ws: WebSocket): void {
    if (ws.readyState === WebSocket.OPEN) {
      // Send state with limited log entries for initial connection
      // This prevents 2MB+ payloads from blocking the UI
      const fullLogEntries = this.state.logEntries;
      const truncatedLogs = fullLogEntries.slice(-DevServer.MAX_INITIAL_LOG_ENTRIES);
      const wasTruncated = fullLogEntries.length > DevServer.MAX_INITIAL_LOG_ENTRIES;

      // Create state with truncated logs for initial send
      const initialState = {
        ...this.state,
        logEntries: truncatedLogs,
      };

      const message = JSON.stringify({ type: 'state', data: initialState });
      console.log(`[STATE] Sending initial state to new client (${message.length} bytes, logs: ${truncatedLogs.length}/${fullLogEntries.length})`);
      ws.send(message);

      // Initialize lastBroadcastState with current state for this client
      // So subsequent updates only send changes
      this.lastBroadcastState = JSON.parse(JSON.stringify(this.state));

      // If we truncated logs, send the rest as a separate update
      // This allows the UI to render immediately with partial logs
      if (wasTruncated) {
        setTimeout(() => {
          if (ws.readyState === WebSocket.OPEN) {
            const logsMessage = JSON.stringify({
              type: 'update',
              data: { logEntries: fullLogEntries }
            });
            console.log(`[STATE] Sending remaining logs (${logsMessage.length} bytes, ${fullLogEntries.length} entries)`);
            ws.send(logsMessage);
          }
        }, 100); // Small delay to let UI render first
      }
    }
  }

  /**
   * Queue a state field for broadcast. Updates are debounced and batched.
   */
  private queueUpdate(...fields: (keyof AppState)[]): void {
    for (const field of fields) {
      this.pendingUpdates.add(field);
    }

    // Debounce: wait 16ms (one frame) to batch multiple updates
    if (this.updateTimeout) {
      clearTimeout(this.updateTimeout);
    }
    this.updateTimeout = setTimeout(() => {
      this.flushUpdates();
    }, 16);
  }

  /**
   * Fast comparison for log entries - logs are append-only so we just compare length
   */
  private logEntriesChanged(): boolean {
    const current = this.state.logEntries;
    const last = this.lastBroadcastState.logEntries || [];
    return current.length !== last.length;
  }

  /**
   * Flush pending updates - only send fields that actually changed.
   */
  private flushUpdates(): void {
    if (this.pendingUpdates.size === 0) return;

    const updates: Partial<AppState> = {};
    let hasChanges = false;

    // Convert Set to Array for ES5-compatible iteration
    const fields = Array.from(this.pendingUpdates);
    for (let i = 0; i < fields.length; i++) {
      const field = fields[i];
      const currentValue = this.state[field];
      const lastValue = this.lastBroadcastState[field];

      // Fast path for logEntries - skip expensive deep comparison
      if (field === 'logEntries') {
        if (this.logEntriesChanged()) {
          // Only send NEW entries (append-only optimization)
          const lastLength = (this.lastBroadcastState.logEntries || []).length;
          const newEntries = this.state.logEntries.slice(lastLength);
          if (newEntries.length > 0) {
            // Send incremental update with only new entries
            (updates as any)['_appendLogEntries'] = newEntries;
            this.lastBroadcastState.logEntries = [...this.state.logEntries];
            hasChanges = true;
          }
        }
        continue;
      }

      if (!deepEqual(currentValue, lastValue)) {
        (updates as any)[field] = currentValue;
        // Deep copy - handle undefined values safely
        if (currentValue === undefined) {
          (this.lastBroadcastState as any)[field] = undefined;
        } else {
          (this.lastBroadcastState as any)[field] = JSON.parse(JSON.stringify(currentValue));
        }
        hasChanges = true;
      }
    }

    this.pendingUpdates.clear();

    if (hasChanges) {
      const message = JSON.stringify({ type: 'update', data: updates });
      const fieldNames = Object.keys(updates);
      console.log(`[STATE] Broadcasting update: ${fieldNames.join(', ')} (${message.length} bytes)`);

      // Convert Set to Array for ES5-compatible iteration
      const clientList = Array.from(this.clients);
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        if (client.readyState === WebSocket.OPEN) {
          client.send(message);
        }
      }
    }
  }

  /**
   * @deprecated Use queueUpdate() for efficient partial updates.
   * This still sends full state - only use for initial connection.
   */
  private broadcastState(): void {
    // Queue all fields for update check
    const allFields = Object.keys(this.state) as (keyof AppState)[];
    this.queueUpdate(...allFields);
  }

  // NOTE: startPolling() removed - using WebSocket events instead

  /**
   * Create a new project via the Python backend.
   */
  private async createProject(parentDirectory?: string, name?: string): Promise<void> {
    // Use first workspace path as default parent directory
    const parent = parentDirectory || this.workspacePaths[0];
    if (!parent) {
      console.error('No workspace path available for project creation');
      return;
    }

    try {
      const response = await this.httpPost(`${DASHBOARD_URL}/api/project/create`, {
        parent_directory: parent,
        name: name || null,
      });

      const result = JSON.parse(response);
      console.log('Project created:', result);

      if (result.success && result.project_root) {
        // Refresh projects to include the new one
        await this.fetchProjects();

        // Select the new project
        this.state.selectedProjectRoot = result.project_root;
      }
    } catch (e) {
      console.error('Failed to create project:', e);
    }
  }

  /**
   * Rename a project via the Python backend.
   */
  private async renameProject(projectRoot: string, newName: string): Promise<void> {
    if (!projectRoot || !newName) {
      console.error('Missing project root or new name for rename');
      return;
    }

    try {
      const response = await this.httpPost(`${DASHBOARD_URL}/api/project/rename`, {
        project_root: projectRoot,
        new_name: newName,
      });

      const result = JSON.parse(response);
      console.log('Project renamed:', result);

      if (result.success && result.new_root) {
        // Refresh projects with the renamed project
        await this.fetchProjects();

        // Update selection to new path
        if (this.state.selectedProjectRoot === projectRoot) {
          this.state.selectedProjectRoot = result.new_root;
        }
      }
    } catch (e) {
      console.error('Failed to rename project:', e);
    }
  }

  /**
   * Fetch all data from the Python backend.
   */
  private async fetchAll(): Promise<void> {
    await Promise.all([
      this.fetchProjects(),
      this.fetchBuilds(),
      this.fetchStdlib(),
      this.fetchPackages(),
      this.fetchAtopileVersions(),
      this.fetchAtopieBranches(),
      this.fetchProblems(),
    ]);

    // Fetch BOM for initially selected project (after projects are loaded)
    if (this.state.selectedProjectRoot) {
      await this.fetchBOM(this.state.selectedProjectRoot, 'default');
    }
  }

  /**
   * Fetch projects from the Python backend.
   */
  private async fetchProjects(): Promise<void> {
    try {
      // Build the URL with workspace paths as query parameter
      const pathsParam = this.workspacePaths.length > 0
        ? `?paths=${encodeURIComponent(this.workspacePaths.join(','))}`
        : '';

      const response = await this.httpGet(`${DASHBOARD_URL}/api/projects${pathsParam}`);
      const data: ProjectsResponse = JSON.parse(response);

      this.state.projects = data.projects;
      this.state.isConnected = true;

      console.log(`Fetched ${data.total} projects from backend`);

      // Auto-select first project if none selected
      if (!this.state.selectedProjectRoot && data.projects.length > 0) {
        this.state.selectedProjectRoot = data.projects[0].root;
        this.state.selectedTargetNames = data.projects[0].targets.map(t => t.name);
        this.queueUpdate('projects', 'isConnected', 'selectedProjectRoot', 'selectedTargetNames');
      } else {
        this.queueUpdate('projects', 'isConnected');
      }
    } catch (e) {
      console.log('Failed to fetch projects from backend');
      // No mock data fallback - wait for real data
    }
  }

  /**
   * Fetch builds from the Python backend.
   */
  private async fetchBuilds(): Promise<void> {
    try {
      const response = await this.httpGet(`${DASHBOARD_URL}/api/summary`);
      const summary: BuildSummaryResponse = JSON.parse(response);

      if (summary.builds) {
        // Build a set of names from the summary for fast lookup
        const summaryBuildNames = new Set(summary.builds.map(b => b.name));
        const summaryBuildDisplayNames = new Set(summary.builds.map(b => b.display_name));

        // Merge summary builds with existing builds to preserve live stage data
        const mergedBuilds = summary.builds.map(summaryBuild => {
          const existing = this.state.builds.find(
            b => b.name === summaryBuild.name || b.display_name === summaryBuild.display_name
          );

          // If we have existing stages from live polling and summary has no stages,
          // preserve the live stages (they have display_name)
          if (existing?.stages && existing.stages.length > 0) {
            const existingHasLiveStages = existing.stages.some(s => s.display_name);
            const summaryHasStages = summaryBuild.stages && summaryBuild.stages.length > 0;

            if (existingHasLiveStages && !summaryHasStages) {
              // Preserve live stages, update other fields
              return {
                ...summaryBuild,
                stages: existing.stages,
                // Also preserve live status if build is still active
                status: existing.status === 'building' || existing.status === 'queued'
                  ? existing.status
                  : summaryBuild.status,
              };
            }
          }

          // If existing build is actively building, preserve its status and stages
          if (existing && (existing.status === 'building' || existing.status === 'queued')) {
            return {
              ...summaryBuild,
              status: existing.status,
              elapsed_seconds: existing.elapsed_seconds,
              stages: existing.stages || summaryBuild.stages,
            };
          }

          return summaryBuild;
        });

        // Also include any active builds that aren't in the summary yet
        // (builds that just started and haven't completed)
        for (const existingBuild of this.state.builds) {
          if (existingBuild.status === 'building' || existingBuild.status === 'queued') {
            const inSummary = summaryBuildNames.has(existingBuild.name) ||
                             summaryBuildDisplayNames.has(existingBuild.display_name);
            if (!inSummary) {
              // This is an active build not yet in summary - keep it
              mergedBuilds.push(existingBuild);
            }
          }
        }

        this.state.builds = mergedBuilds;
        this.state.isConnected = true;

        // Note: No auto-selection of builds - let users manually select
        // to avoid overriding "All" selection or user preferences

        this.queueUpdate('builds', 'isConnected');
      }
    } catch (e) {
      // Dashboard not available
      if (this.state.isConnected) {
        console.log('Dashboard not available');
        this.state.isConnected = false;
        this.queueUpdate('isConnected');
      }
    }
  }

  /**
   * Fetch standard library from the Python backend.
   */
  private async fetchStdlib(): Promise<void> {
    this.state.isLoadingStdlib = true;
    this.queueUpdate('isLoadingStdlib');

    try {
      const response = await this.httpGet(`${DASHBOARD_URL}/api/stdlib`);
      const data: StdLibResponse = JSON.parse(response);

      this.state.stdlibItems = data.items;
      this.state.isLoadingStdlib = false;
      console.log(`Fetched ${data.total} standard library items from backend`);
      this.queueUpdate('stdlibItems', 'isLoadingStdlib');
    } catch (e) {
      console.log('Failed to fetch stdlib from backend, using mock data');
      this.state.stdlibItems = this.createMockStdlib();
      this.state.isLoadingStdlib = false;
      this.queueUpdate('stdlibItems', 'isLoadingStdlib');
    }
  }

  /**
   * Fetch packages from the Python backend.
   * Fetches both installed packages and registry packages, then merges them.
   */
  private async fetchPackages(): Promise<void> {
    this.state.isLoadingPackages = true;
    this.queueUpdate('isLoadingPackages');

    try {
      const pathsParam = this.workspacePaths.length > 0
        ? `?paths=${encodeURIComponent(this.workspacePaths.join(','))}`
        : '';

      // Fetch installed packages
      const installedResponse = await this.httpGet(`${DASHBOARD_URL}/api/packages${pathsParam}`);
      const installedData: PackagesResponse = JSON.parse(installedResponse);
      const installedPackages = installedData.packages || [];

      // Try to fetch registry packages to augment with latest versions
      // Note: empty query returns 0 results from the registry API, so we use
      // "atopile" as the default query since most packages are from atopile
      let registryPackages: PackageInfo[] = [];
      try {
        const registryPathsParam = this.workspacePaths.length > 0
          ? `&paths=${encodeURIComponent(this.workspacePaths.join(','))}`
          : '';
        const registryResponse = await this.httpGet(
          `${DASHBOARD_URL}/api/registry/search?query=atopile${registryPathsParam}`
        );
        const registryData: RegistrySearchResponse = JSON.parse(registryResponse);
        registryPackages = registryData.packages || [];
      } catch (e) {
        console.log('Registry search not available, using installed packages only');
      }

      // Merge installed with registry data
      const packageMap = new Map<string, PackageInfo>();

      // Add installed packages
      for (const pkg of installedPackages) {
        packageMap.set(pkg.identifier, pkg);
      }

      // Add registry packages (or update with latest_version)
      for (const pkg of registryPackages) {
        if (packageMap.has(pkg.identifier)) {
          // Update with registry data
          const existing = packageMap.get(pkg.identifier)!;
          packageMap.set(pkg.identifier, {
            ...existing,
            latest_version: pkg.latest_version,
            summary: existing.summary || pkg.summary,
            description: existing.description || pkg.description,
            homepage: existing.homepage || pkg.homepage,
            repository: existing.repository || pkg.repository,
          });
        } else {
          // Add uninstalled registry package
          packageMap.set(pkg.identifier, pkg);
        }
      }

      this.state.packages = Array.from(packageMap.values());
      this.state.isLoadingPackages = false;
      console.log(`Fetched ${this.state.packages.length} packages (${installedPackages.length} installed, ${registryPackages.length} from registry)`);
      this.queueUpdate('packages', 'isLoadingPackages');
    } catch (e) {
      console.log('Failed to fetch packages from backend, using mock data');
      this.state.packages = this.createMockPackages();
      this.state.isLoadingPackages = false;
      this.queueUpdate('packages', 'isLoadingPackages');
    }
  }

  /**
   * Fetch BOM (Bill of Materials) from the Python backend.
   */
  private async fetchBOM(projectRoot?: string, target: string = 'default'): Promise<void> {
    // Use provided projectRoot or fall back to selected project
    const root = projectRoot || this.state.selectedProjectRoot;
    if (!root) {
      console.log('No project root for BOM fetch');
      return;
    }

    this.state.isLoadingBOM = true;
    this.state.bomError = null;
    this.queueUpdate('isLoadingBOM', 'bomError');

    try {
      const params = new URLSearchParams({
        project_root: root,
        target: target,
      });
      const response = await this.httpGet(`${DASHBOARD_URL}/api/bom?${params}`);
      const data: BOMData = JSON.parse(response);

      this.state.bomData = data;
      this.state.isLoadingBOM = false;
      this.state.bomError = null;
      console.log(`Fetched BOM with ${data.components?.length || 0} components`);
      this.queueUpdate('bomData', 'isLoadingBOM', 'bomError');
    } catch (e: any) {
      console.log('Failed to fetch BOM:', e.message || e);
      this.state.bomData = null;
      this.state.isLoadingBOM = false;
      this.state.bomError = e.message || 'Failed to fetch BOM';
      this.queueUpdate('bomData', 'isLoadingBOM', 'bomError');
    }
  }

  /**
   * Fetch problems (errors/warnings) from the Python backend.
   */
  private async fetchProblems(projectRoot?: string, buildName?: string): Promise<void> {
    this.state.isLoadingProblems = true;
    this.queueUpdate('isLoadingProblems');

    try {
      const params = new URLSearchParams();
      if (projectRoot) {
        params.set('project_root', projectRoot);
      }
      if (buildName) {
        params.set('build_name', buildName);
      }

      const response = await this.httpGet(`${DASHBOARD_URL}/api/problems?${params}`);
      const data: ProblemsResponse = JSON.parse(response);

      // Convert snake_case from backend to camelCase for frontend
      this.state.problems = data.problems.map((p, idx) => ({
        id: `${p.build_name || 'unknown'}-${idx}`,
        level: p.level as 'error' | 'warning',
        message: p.message,
        file: p.file || undefined,
        line: p.line || undefined,
        column: p.column || undefined,
        stage: p.stage || undefined,
        logger: p.logger || undefined,
        buildName: p.build_name || undefined,
        projectName: p.project_name || undefined,
        timestamp: p.timestamp || undefined,
        ato_traceback: p.ato_traceback || undefined,
      }));
      this.state.isLoadingProblems = false;
      console.log(`Fetched ${data.total} problems (${data.error_count} errors, ${data.warning_count} warnings)`);
      this.queueUpdate('problems', 'isLoadingProblems');
    } catch (e: any) {
      console.log('Failed to fetch problems:', e.message || e);
      this.state.problems = [];
      this.state.isLoadingProblems = false;
      this.queueUpdate('problems', 'isLoadingProblems');
    }
  }

  /**
   * Fetch detailed package info from the registry.
   */
  private async fetchPackageDetails(packageId: string): Promise<void> {
    this.state.isLoadingPackageDetails = true;
    this.state.packageDetailsError = null;
    this.queueUpdate('isLoadingPackageDetails', 'packageDetailsError');

    try {
      const pathsParam = this.workspacePaths.length > 0
        ? `?paths=${encodeURIComponent(this.workspacePaths.join(','))}`
        : '';

      // Note: Don't encode the packageId as it contains a slash (e.g., "atopile/bosch-bme280")
      // and FastAPI expects the path format, not URL-encoded
      const response = await this.httpGet(
        `${DASHBOARD_URL}/api/packages/${packageId}/details${pathsParam}`
      );
      const data: PackageDetails = JSON.parse(response);

      this.state.selectedPackageDetails = data;
      this.state.isLoadingPackageDetails = false;
      console.log(`Fetched details for ${packageId}: ${data.version_count} versions, ${data.downloads || 0} downloads`);
      this.queueUpdate('selectedPackageDetails', 'isLoadingPackageDetails');
    } catch (e: any) {
      console.log('Failed to fetch package details:', e.message || e);
      this.state.selectedPackageDetails = null;
      this.state.isLoadingPackageDetails = false;
      this.state.packageDetailsError = e.message || 'Failed to fetch package details';
      this.queueUpdate('selectedPackageDetails', 'isLoadingPackageDetails', 'packageDetailsError');
    }
  }

  /**
   * Build a package - first installs if needed, then builds.
   * This is useful for building packages from the registry without a project.
   */
  private async buildPackage(
    packageId: string,
    projectRoot: string,
    entry?: string
  ): Promise<void> {
    // First, check if package is installed
    const pkg = this.state.packages.find(p => p.identifier === packageId);
    const isInstalled = pkg?.installed && pkg.installed_in.some(
      path => path === projectRoot || path.endsWith(`/${projectRoot}`) || projectRoot.endsWith(path)
    );

    if (!isInstalled) {
      // Install the package first
      console.log(`Package ${packageId} not installed, installing first...`);
      await this.installPackage(packageId, projectRoot);

      // Wait for installation (poll for a bit)
      let attempts = 0;
      while (attempts < 10) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await this.fetchPackages();
        const updatedPkg = this.state.packages.find(p => p.identifier === packageId);
        if (updatedPkg?.installed) {
          console.log(`Package ${packageId} installed successfully`);
          break;
        }
        attempts++;
      }
    }

    // Now trigger the build
    // For packages, we want to build the default entry point
    // The entry format is usually "package-name.ato:ModuleName"
    const parts = packageId.split('/');
    const pkgName = parts[parts.length - 1];
    const defaultEntry = entry || `${pkgName}.ato:${pkgName.replace(/-/g, '_')}`;

    console.log(`Building package with entry: ${defaultEntry}`);

    // Trigger a build for this entry point
    // Use the project root where the package is installed
    await this.triggerBuild({
      level: 'build',
      id: `${projectRoot}:default`,  // Use default build target
      projectRoot: projectRoot,
      targets: ['default'],
    });
  }

  /**
   * Cancel a running build.
   */
  private async cancelBuild(buildId: string): Promise<void> {
    try {
      const response = await this.httpPost(`${DASHBOARD_URL}/api/build/${buildId}/cancel`, {});
      const data = JSON.parse(response);
      console.log('Build cancelled:', data);

      // Refresh builds to get the updated status
      await this.fetchBuilds();
    } catch (e: any) {
      console.error('Failed to cancel build:', e.message || e);
    }
  }

  /**
   * Handle opening a file, resolving atopile addresses if needed.
   */
  private async handleOpenFile(message: any): Promise<void> {
    let { file, line, column } = message;

    // If the file looks like an atopile address (contains ::), resolve it first
    if (file && file.includes('::')) {
      try {
        const params = new URLSearchParams({ address: file });
        if (this.state.selectedProjectRoot) {
          params.append('project_root', this.state.selectedProjectRoot);
        }

        const response = await this.httpGet(`${DASHBOARD_URL}/api/resolve-location?${params}`);
        const data = JSON.parse(response);

        if (data) {
          file = data.file;
          line = data.line || line;
          column = data.column || column;
          console.log(`Resolved address to: ${file}:${line}`);
        }
      } catch (e: any) {
        console.log('Failed to resolve address:', e.message || e);
        // Continue with original - will likely fail but better than nothing
      }
    }

    // Open the file using Cursor's `cursor` command (or VS Code's `code` as fallback)
    if (file) {
      const { exec } = await import('child_process');
      const location = `${file}:${line || 1}:${column || 1}`;
      console.log(`[Dev] Opening file: ${location}`);

      // Try cursor first (for Cursor IDE), then fall back to code (for VS Code)
      exec(`cursor -g "${location}"`, (cursorError) => {
        if (cursorError) {
          // Cursor command failed, try VS Code
          exec(`code -g "${location}"`, (codeError) => {
            if (codeError) {
              console.error(`Failed to open file: ${codeError.message}`);
            }
          });
        }
      });
    }
  }

  /**
   * Open the source file for a build entry point.
   * Entry format: "file.ato:Module" or just "file.ato"
   */
  private async handleOpenSource(projectId: string, entry: string): Promise<void> {
    console.log(`[Dev] Opening source for entry: ${entry} in project: ${projectId}`);

    // Find the project to get the root path
    const project = this.state.projects.find(p => p.root === projectId || p.name === projectId);
    const projectRoot = project?.root || projectId;

    // Parse the entry point - format is usually "file.ato:Module"
    const [fileName] = entry.split(':');
    if (!fileName) {
      console.error('Invalid entry format:', entry);
      return;
    }

    // Construct the full file path
    const filePath = `${projectRoot}/${fileName}`;

    // Open using cursor/code
    const { exec } = await import('child_process');
    console.log(`[Dev] Opening file: ${filePath}`);

    exec(`cursor -g "${filePath}"`, (cursorError) => {
      if (cursorError) {
        exec(`code -g "${filePath}"`, (codeError) => {
          if (codeError) {
            console.error(`Failed to open file: ${codeError.message}`);
          }
        });
      }
    });
  }

  /**
   * Open the layout file in KiCad.
   */
  private async handleOpenKiCad(projectId: string, buildId: string): Promise<void> {
    console.log(`[Dev] Opening KiCad for project: ${projectId}, build: ${buildId}`);

    // Find the project to get the root path
    const project = this.state.projects.find(p => p.root === projectId || p.name === projectId);
    const projectRoot = project?.root || projectId;

    // Resolve any .. in the path
    const path = await import('path');
    const resolvedRoot = path.resolve(projectRoot);

    // Layout files are in layouts/<target>/<target>.kicad_pcb
    const layoutPath = `${resolvedRoot}/layouts/${buildId}/${buildId}.kicad_pcb`;

    const { exec } = await import('child_process');
    console.log(`[Dev] Opening KiCad: ${layoutPath}`);

    // Check if file exists first
    const fsPromises = await import('fs/promises');
    try {
      await fsPromises.access(layoutPath);
    } catch {
      console.error(`Layout file not found: ${layoutPath}`);
      return;
    }

    // Try to open with 'open' command on macOS (uses default app)
    exec(`open "${layoutPath}"`, (error) => {
      if (error) {
        console.error(`Failed to open with 'open': ${error.message}`);
      }
    });
  }

  /**
   * Open the layout preview.
   */
  private async handleOpenLayout(projectId: string, buildId: string): Promise<void> {
    console.log(`[Dev] Opening layout preview for project: ${projectId}, build: ${buildId}`);

    // Find the project to get the root path
    const project = this.state.projects.find(p => p.root === projectId || p.name === projectId);
    const projectRoot = project?.root || projectId;

    // Resolve any .. in the path
    const resolvedRoot = path.resolve(projectRoot);

    // Layout file path
    const layoutPath = `${resolvedRoot}/layouts/${buildId}/${buildId}.kicad_pcb`;

    // Check if file exists
    if (!fs.existsSync(layoutPath)) {
      console.error(`Layout file not found: ${layoutPath}`);
      return;
    }

    // Open the viewer page with the file path
    const viewerUrl = `http://localhost:${HTTP_SERVER_PORT}/layout?file=${encodeURIComponent(layoutPath)}`;

    const { exec } = await import('child_process');
    console.log(`[Dev] Opening layout preview: ${viewerUrl}`);

    exec(`open "${viewerUrl}"`, (error) => {
      if (error) {
        console.error(`Failed to open layout preview: ${error.message}`);
      }
    });
  }

  /**
   * Open the 3D viewer.
   */
  private async handleOpen3D(projectId: string, buildId: string): Promise<void> {
    console.log(`[Dev] Opening 3D viewer for project: ${projectId}, build: ${buildId}`);

    // Find the project to get the root path
    const project = this.state.projects.find(p => p.root === projectId || p.name === projectId);
    const projectRoot = project?.root || projectId;

    // Resolve any .. in the path
    const resolvedRoot = path.resolve(projectRoot);

    // 3D model path - look for .glb file in build output
    // Convention: build/builds/<target>/<target>.glb
    const modelPath = `${resolvedRoot}/build/builds/${buildId}/${buildId}.glb`;

    // Check if file exists
    if (!fs.existsSync(modelPath)) {
      console.error(`3D model file not found: ${modelPath}`);
      console.log(`[Dev] 3D model needs to be generated first. Try running a build.`);
      return;
    }

    // Open the viewer page with the file path
    const viewerUrl = `http://localhost:${HTTP_SERVER_PORT}/3d?file=${encodeURIComponent(modelPath)}`;

    const { exec } = await import('child_process');
    console.log(`[Dev] Opening 3D viewer: ${viewerUrl}`);

    exec(`open "${viewerUrl}"`, (error) => {
      if (error) {
        console.error(`Failed to open 3D viewer: ${error.message}`);
      }
    });
  }

  /**
   * Install a package into a project.
   */
  private async installPackage(packageId: string, projectRoot: string, version?: string): Promise<void> {
    try {
      const response = await this.httpPost(`${DASHBOARD_URL}/api/packages/install`, {
        package_identifier: packageId,
        project_root: projectRoot,
        version: version || null,
      });
      const result = JSON.parse(response);
      console.log('Package install result:', result);

      // Refresh packages after install
      setTimeout(() => this.fetchPackages(), 2000);
    } catch (e) {
      console.error('Failed to install package:', e);
    }
  }

  /**
   * Remove a package from a project.
   */
  private async removePackage(packageId: string, projectRoot: string): Promise<void> {
    try {
      const response = await this.httpPost(`${DASHBOARD_URL}/api/packages/remove`, {
        package_identifier: packageId,
        project_root: projectRoot,
      });
      const result = JSON.parse(response);
      console.log('Package remove result:', result);

      // Refresh packages after remove
      setTimeout(() => this.fetchPackages(), 2000);
    } catch (e) {
      console.error('Failed to remove package:', e);
    }
  }

  // --- Atopile Version Management ---

  /**
   * Fetch available atopile versions from PyPI.
   */
  private async fetchAtopileVersions(): Promise<void> {
    try {
      const response = await this.httpsGet('https://pypi.org/pypi/atopile/json');
      const data = JSON.parse(response);

      // Get all version keys and sort them in descending order
      const versions = Object.keys(data.releases || {})
        .filter(v => !v.includes('dev') && !v.includes('rc') && !v.includes('alpha') && !v.includes('beta'))
        .sort((a, b) => {
          // Parse version numbers for proper sorting
          const partsA = a.split('.').map(Number);
          const partsB = b.split('.').map(Number);
          for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
            const numA = partsA[i] || 0;
            const numB = partsB[i] || 0;
            if (numA !== numB) return numB - numA;
          }
          return 0;
        })
        .slice(0, 20); // Keep latest 20 versions

      this.state.atopile.availableVersions = versions;
      console.log(`Fetched ${versions.length} atopile versions from PyPI`);
    } catch (e) {
      console.error('Failed to fetch atopile versions:', e);
    }
  }

  /**
   * Set the atopile version (simulates installation in dev mode).
   */
  private async setAtopileVersion(version: string): Promise<void> {
    // Simulate installation progress
    this.state.atopile.isInstalling = true;
    this.state.atopile.installProgress = { message: 'Downloading atopile...', percent: 0 };
    this.queueUpdate('atopile');

    // Simulate progress updates
    const steps = [
      { message: 'Downloading atopile...', percent: 20 },
      { message: 'Installing dependencies...', percent: 50 },
      { message: 'Configuring environment...', percent: 80 },
      { message: 'Verifying installation...', percent: 95 },
    ];

    for (const step of steps) {
      await this.sleep(500);
      this.state.atopile.installProgress = step;
      this.queueUpdate('atopile');
    }

    await this.sleep(500);

    // Complete installation
    this.state.atopile.currentVersion = version;
    this.state.atopile.isInstalling = false;
    this.state.atopile.installProgress = null;
    this.queueUpdate('atopile');
    console.log(`Atopile version set to ${version}`);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Fetch available atopile branches from the dashboard API.
   * Falls back to GitHub API if dashboard is unavailable.
   */
  private async fetchAtopieBranches(): Promise<void> {
    // Try dashboard API first (handles caching)
    try {
      const response = await this.httpGet(`${DASHBOARD_URL}/api/atopile/branches`);
      const data = JSON.parse(response);
      const branches = data.branches || [];

      if (branches.length > 0) {
        this.state.atopile.availableBranches = branches;
        const cached = data.cached ? ' (cached)' : '';
        console.log(`Fetched ${branches.length} atopile branches from dashboard${cached}`);
        return;
      }
    } catch (e) {
      console.log('Dashboard unavailable for branches, falling back to GitHub API');
    }

    // Fall back to direct GitHub API
    try {
      const response = await this.httpsGet('https://api.github.com/repos/atopile/atopile/branches?per_page=100');
      const data = JSON.parse(response);

      // Extract branch names and sort them
      const branches = (data || [])
        .map((b: any) => b.name)
        .filter((name: string) => name)
        .sort((a: string, b: string) => {
          if (a === 'main') return -1;
          if (b === 'main') return 1;
          if (a === 'develop') return -1;
          if (b === 'develop') return 1;
          return a.localeCompare(b);
        });

      this.state.atopile.availableBranches = branches;
      console.log(`Fetched ${branches.length} atopile branches from GitHub`);
    } catch (e) {
      console.error('Failed to fetch atopile branches:', e);
      this.state.atopile.availableBranches = ['main', 'develop'];
    }
  }

  /**
   * Set the atopile branch (simulates installation in dev mode).
   */
  private async setAtopieBranch(branch: string): Promise<void> {
    // Simulate installation progress
    this.state.atopile.isInstalling = true;
    this.state.atopile.installProgress = { message: `Cloning branch ${branch}...`, percent: 0 };
    this.queueUpdate('atopile');

    // Simulate progress updates
    const steps = [
      { message: `Cloning branch ${branch}...`, percent: 15 },
      { message: 'Installing from git...', percent: 40 },
      { message: 'Installing dependencies...', percent: 70 },
      { message: 'Configuring environment...', percent: 90 },
    ];

    for (const step of steps) {
      await this.sleep(600);
      this.state.atopile.installProgress = step;
      this.queueUpdate('atopile');
    }

    await this.sleep(500);

    // Complete installation
    this.state.atopile.branch = branch;
    this.state.atopile.currentVersion = `git@${branch}`;
    this.state.atopile.isInstalling = false;
    this.state.atopile.installProgress = null;
    this.queueUpdate('atopile');
    console.log(`Atopile branch set to ${branch}`);
  }

  /**
   * HTTPS GET request helper.
   */
  private httpsGet(url: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const https = require('https');
      const parsedUrl = new URL(url);
      const options = {
        hostname: parsedUrl.hostname,
        path: parsedUrl.pathname + parsedUrl.search,
        headers: {
          'User-Agent': 'atopile-vscode-extension',
        },
      };
      https.get(options, (res: any) => {
        let data = '';
        res.on('data', (chunk: string) => { data += chunk; });
        res.on('end', () => resolve(data));
      }).on('error', reject);
    });
  }

  /**
   * Search the package registry.
   */
  private async searchRegistry(query: string): Promise<void> {
    this.state.isSearchingRegistry = true;
    this.state.registrySearchQuery = query;
    this.queueUpdate('isSearchingRegistry', 'registrySearchQuery');

    try {
      const pathsParam = this.workspacePaths.length > 0
        ? `&paths=${encodeURIComponent(this.workspacePaths.join(','))}`
        : '';

      const response = await this.httpGet(
        `${DASHBOARD_URL}/api/registry/search?query=${encodeURIComponent(query)}${pathsParam}`
      );
      const data: RegistrySearchResponse = JSON.parse(response);

      this.state.registryResults = data.packages;
      this.state.isSearchingRegistry = false;
      console.log(`Found ${data.total} packages for query: "${query}"`);
      this.queueUpdate('registryResults', 'isSearchingRegistry');
    } catch (e) {
      console.log('Failed to search registry:', e);
      this.state.registryResults = [];
      this.state.isSearchingRegistry = false;
      this.queueUpdate('registryResults', 'isSearchingRegistry');
    }
  }

  /**
   * Create mock packages for when backend is unavailable.
   */
  private createMockPackages(): PackageInfo[] {
    return [
      {
        identifier: 'atopile/bosch-bme280',
        name: 'bosch-bme280',
        publisher: 'atopile',
        version: '0.1.2',
        description: 'Bosch BME280 environmental sensor',
        installed: true,
        installed_in: ['/Users/demo/projects/my-board'],
      },
      {
        identifier: 'atopile/espressif-esp32-s3',
        name: 'espressif-esp32-s3',
        publisher: 'atopile',
        version: '0.1.0',
        description: 'ESP32-S3 WiFi+BLE module',
        installed: true,
        installed_in: ['/Users/demo/projects/my-board'],
      },
    ];
  }

  /**
   * Create mock stdlib for when backend is unavailable.
   */
  private createMockStdlib(): StdLibItem[] {
    return [
      {
        id: 'Electrical',
        name: 'Electrical',
        type: 'interface',
        description: 'Base electrical connection point. Represents a single electrical node.',
        usage: `signal my_signal = new Electrical
resistor.p1 ~ my_signal`,
        children: [],
        parameters: [],
      },
      {
        id: 'ElectricPower',
        name: 'ElectricPower',
        type: 'interface',
        description: 'Power supply interface with high and low voltage rails. Use for VCC/GND connections.',
        usage: `power = new ElectricPower
power.hv ~ vcc_pin
power.lv ~ gnd_pin
assert power.voltage within 3.0V to 3.6V`,
        children: [
          { name: 'hv', type: 'Electrical', item_type: 'interface', children: [] },
          { name: 'lv', type: 'Electrical', item_type: 'interface', children: [] },
          { name: 'voltage', type: 'V', item_type: 'parameter', children: [] },
          { name: 'max_current', type: 'A', item_type: 'parameter', children: [] },
        ],
        parameters: [],
      },
      {
        id: 'I2C',
        name: 'I2C',
        type: 'interface',
        description: 'I²C bus interface with clock and data lines. Supports address configuration.',
        usage: `i2c_bus = new I2C
i2c_bus ~ sensor.i2c
assert i2c_bus.frequency within 100kHz to 400kHz`,
        children: [
          { name: 'scl', type: 'ElectricLogic', item_type: 'interface', children: [] },
          { name: 'sda', type: 'ElectricLogic', item_type: 'interface', children: [] },
          { name: 'frequency', type: 'Hz', item_type: 'parameter', children: [] },
          { name: 'address', type: 'Bit', item_type: 'parameter', children: [] },
        ],
        parameters: [],
      },
      {
        id: 'Resistor',
        name: 'Resistor',
        type: 'module',
        description: 'Generic resistor with automatic part selection based on constraints.',
        usage: `r1 = new Resistor
r1.resistance = 10kohm +/- 5%
r1.package = "0402"
power.hv ~> r1 ~> led.anode`,
        children: [
          { name: 'unnamed[]', type: 'Electrical[2]', item_type: 'interface', children: [] },
          { name: 'resistance', type: 'ohm', item_type: 'parameter', children: [] },
          { name: 'max_power', type: 'W', item_type: 'parameter', children: [] },
          { name: 'max_voltage', type: 'V', item_type: 'parameter', children: [] },
        ],
        parameters: [],
      },
      {
        id: 'Capacitor',
        name: 'Capacitor',
        type: 'module',
        description: 'Generic capacitor with automatic part selection. Supports ceramic, electrolytic.',
        usage: `c1 = new Capacitor
c1.capacitance = 100nF +/- 20%
c1.package = "0402"
power.hv ~> c1 ~> power.lv`,
        children: [
          { name: 'unnamed[]', type: 'Electrical[2]', item_type: 'interface', children: [] },
          { name: 'capacitance', type: 'F', item_type: 'parameter', children: [] },
          { name: 'max_voltage', type: 'V', item_type: 'parameter', children: [] },
        ],
        parameters: [],
      },
      {
        id: 'can_bridge',
        name: 'can_bridge',
        type: 'trait',
        description: 'Marks a module as bridgeable, enabling the ~> operator for series connections.',
        usage: `# Modules with can_bridge trait:
power.hv ~> resistor ~> led.anode
input ~> capacitor ~> output`,
        children: [],
        parameters: [],
      },
    ];
  }

  private httpGet(url: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const req = http.request(url, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => resolve(data));
      });
      req.on('error', reject);
      req.setTimeout(5000, () => {
        req.destroy();
        reject(new Error('Timeout'));
      });
      req.end();
    });
  }

  private httpPost(url: string, body: object): Promise<string> {
    return new Promise((resolve, reject) => {
      const bodyStr = JSON.stringify(body);
      const parsedUrl = new URL(url);

      const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port,
        path: parsedUrl.pathname,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(bodyStr),
        },
      };

      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          if (res.statusCode && res.statusCode >= 400) {
            reject(new Error(`HTTP ${res.statusCode}: ${data}`));
          } else {
            resolve(data);
          }
        });
      });

      req.on('error', reject);
      req.setTimeout(30000, () => {  // 30s timeout for builds
        req.destroy();
        reject(new Error('Timeout'));
      });

      req.write(bodyStr);
      req.end();
    });
  }

  /**
   * Start HTTP server for serving viewer pages and files.
   */
  private startHttpServer(): void {
    this.httpServer = http.createServer((req, res) => {
      const url = new URL(req.url || '/', `http://localhost:${HTTP_SERVER_PORT}`);

      // Enable CORS
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

      if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
      }

      // Route: /layout - KiCanvas viewer
      if (url.pathname === '/layout') {
        const filePath = url.searchParams.get('file');
        this.serveLayoutViewer(res, filePath);
        return;
      }

      // Route: /3d - 3D Model viewer
      if (url.pathname === '/3d') {
        const filePath = url.searchParams.get('file');
        this.serve3DViewer(res, filePath);
        return;
      }

      // Route: /file/* - Serve raw files (for viewer to load)
      // Path format: /file/Users/... -> extracts /Users/...
      if (url.pathname.startsWith('/file/')) {
        const filePath = '/' + decodeURIComponent(url.pathname.slice(6));
        this.serveFile(res, filePath);
        return;
      }

      // 404
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not Found');
    });

    this.httpServer.listen(HTTP_SERVER_PORT, () => {
      console.log(`HTTP Server for viewers listening on http://localhost:${HTTP_SERVER_PORT}`);
    });
  }

  private serveLayoutViewer(res: http.ServerResponse, filePath: string | null): void {
    const fileUrl = filePath ? `http://localhost:${HTTP_SERVER_PORT}/file${filePath}` : '';

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Layout Preview</title>
    <script type="module" src="https://kicanvas.org/kicanvas/kicanvas.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100%; width: 100%; overflow: hidden; background: #1e1e2e; color: #cdd6f4; font-family: system-ui, sans-serif; }
        #container { height: 100%; width: 100%; }
        kicanvas-embed { height: 100%; width: 100%; display: block; }
        .error { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 2rem; text-align: center; }
        .error h2 { color: #f38ba8; margin-bottom: 1rem; }
        .error p { color: #a6adc8; max-width: 500px; }
        .error code { background: #313244; padding: 0.5rem 1rem; border-radius: 4px; margin-top: 1rem; display: block; word-break: break-all; }
    </style>
</head>
<body>
    <div id="container">
        ${filePath ? `<kicanvas-embed src="${fileUrl}" controls="full" zoom="objects" controlslist="nodownload"></kicanvas-embed>` : `
        <div class="error">
            <h2>Layout Not Found</h2>
            <p>No layout file specified. Use ?file=/path/to/file.kicad_pcb</p>
        </div>`}
    </div>
</body>
</html>`;

    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
  }

  private serve3DViewer(res: http.ServerResponse, filePath: string | null): void {
    const fileUrl = filePath ? `http://localhost:${HTTP_SERVER_PORT}/file${filePath}` : '';

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Model Preview</title>
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.3.0/model-viewer.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100%; width: 100%; overflow: hidden; background: #1e1e2e; color: #cdd6f4; font-family: system-ui, sans-serif; }
        #container { height: 100%; width: 100%; }
        model-viewer { height: 100%; width: 100%; display: block; --poster-color: transparent; }
        .error { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 2rem; text-align: center; }
        .error h2 { color: #f38ba8; margin-bottom: 1rem; }
        .error p { color: #a6adc8; max-width: 500px; }
    </style>
</head>
<body>
    <div id="container">
        ${filePath ? `<model-viewer src="${fileUrl}" camera-controls tone-mapping="neutral" exposure="1.2" shadow-intensity="0.7" shadow-softness="0.8" auto-rotate></model-viewer>` : `
        <div class="error">
            <h2>3D Model Not Found</h2>
            <p>No model file specified. Use ?file=/path/to/model.glb</p>
        </div>`}
    </div>
</body>
</html>`;

    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
  }

  private serveFile(res: http.ServerResponse, filePath: string): void {
    // Security: ensure path doesn't escape with ..
    const normalizedPath = path.resolve(filePath);

    if (!fs.existsSync(normalizedPath)) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end(`File not found: ${filePath}`);
      return;
    }

    // Determine content type
    const ext = path.extname(normalizedPath).toLowerCase();
    const contentTypes: Record<string, string> = {
      '.kicad_pcb': 'text/plain',
      '.glb': 'model/gltf-binary',
      '.gltf': 'model/gltf+json',
      '.step': 'application/step',
      '.stp': 'application/step',
    };
    const contentType = contentTypes[ext] || 'application/octet-stream';

    try {
      const content = fs.readFileSync(normalizedPath);
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    } catch (error) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end(`Error reading file: ${error}`);
    }
  }

  private createInitialState(): AppState {
    return {
      isConnected: false,
      projects: [],
      selectedProjectRoot: null,
      selectedTargetNames: [],
      builds: [],
      packages: [],
      isLoadingPackages: false,
      registryResults: [],
      isSearchingRegistry: false,
      registrySearchQuery: '',
      selectedBuildName: null,
      selectedProjectName: null,
      selectedStageIds: [],
      logEntries: [],
      isLoadingLogs: false,
      logFile: null,
      enabledLogLevels: ['INFO', 'WARNING', 'ERROR', 'ALERT'],
      logSearchQuery: '',
      logTimestampMode: 'absolute',
      logAutoScroll: true,
      // Log counts (from server)
      logCounts: { DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0, ALERT: 0 },
      logTotalCount: 0,
      logHasMore: false,
      expandedTargets: [],
      version: '0.14.0-dev',
      logoUri: '',
      // Atopile configuration
      atopile: {
        currentVersion: '0.14.0',
        source: 'release' as const,
        localPath: null,
        branch: null,
        availableVersions: ['0.14.0', '0.13.5', '0.13.4', '0.13.3', '0.13.2', '0.13.1', '0.13.0', '0.12.0', '0.11.0'],
        availableBranches: ['main', 'develop', 'feature/fabll', 'feature/fabll_part2'],
        detectedInstallations: [],
        isInstalling: false,
        installProgress: null,
        error: null,
      },
      stdlibItems: [],
      isLoadingStdlib: false,
      // BOM
      bomData: null,
      isLoadingBOM: false,
      bomError: null,
      // Package details
      selectedPackageDetails: null,
      isLoadingPackageDetails: false,
      packageDetailsError: null,
      // Problems
      problems: [],
      isLoadingProblems: false,
    };
  }

  private createMockProjects(): Project[] {
    return [
      {
        root: '/Users/demo/projects/my-board',
        name: 'my-board',
        targets: [
          { name: 'default', entry: 'main.ato:App', root: '/Users/demo/projects/my-board' },
          { name: 'test', entry: 'test.ato:TestApp', root: '/Users/demo/projects/my-board' },
        ],
      },
      {
        root: '/Users/demo/projects/sensor-module',
        name: 'sensor-module',
        targets: [
          { name: 'default', entry: 'sensor.ato:Sensor', root: '/Users/demo/projects/sensor-module' },
        ],
      },
    ];
  }

  private createMockBuilds(): Build[] {
    return [
      {
        name: 'default',
        display_name: 'my-board:default',
        project_name: 'my-board',
        status: 'success',
        elapsed_seconds: 12.5,
        warnings: 2,
        errors: 0,
        return_code: 0,
        stages: [
          { name: 'init', stage_id: 'init', elapsed_seconds: 0.5, status: 'success', infos: 5, warnings: 0, errors: 0, alerts: 0 },
          { name: 'compile', stage_id: 'compile', elapsed_seconds: 3.2, status: 'success', infos: 12, warnings: 1, errors: 0, alerts: 0 },
          { name: 'pick_parts', stage_id: 'pick_parts', elapsed_seconds: 5.1, status: 'warning', infos: 8, warnings: 1, errors: 0, alerts: 0 },
          { name: 'generate', stage_id: 'generate', elapsed_seconds: 3.7, status: 'success', infos: 15, warnings: 0, errors: 0, alerts: 0 },
        ],
      },
      {
        name: 'test',
        display_name: 'my-board:test',
        project_name: 'my-board',
        status: 'failed',
        elapsed_seconds: 8.3,
        warnings: 1,
        errors: 2,
        return_code: 1,
        stages: [
          { name: 'init', stage_id: 'init', elapsed_seconds: 0.4, status: 'success', infos: 3, warnings: 0, errors: 0, alerts: 0 },
          { name: 'compile', stage_id: 'compile', elapsed_seconds: 2.1, status: 'failed', infos: 5, warnings: 1, errors: 2, alerts: 0 },
        ],
      },
    ];
  }

}

// Get workspace paths from command line args
const args = process.argv.slice(2);
const workspacePaths = args.length > 0 ? args : [];

console.log('Workspace paths:', workspacePaths.length > 0 ? workspacePaths : '(none - will use backend defaults)');

// Start the server
const server = new DevServer(workspacePaths);
server.start().then(() => {
  console.log(`
Dev Server started!

  WebSocket: ws://localhost:${DEV_SERVER_PORT}
  Viewers:   http://localhost:${HTTP_SERVER_PORT}
  Backend:   ${DASHBOARD_URL}

Viewer pages:
  - Layout:  http://localhost:${HTTP_SERVER_PORT}/layout?file=/path/to/file.kicad_pcb
  - 3D:      http://localhost:${HTTP_SERVER_PORT}/3d?file=/path/to/file.glb

The dev server fetches data from the Python backend at ${DASHBOARD_URL}.
Make sure the backend is running (starts automatically with 'ato build').

To specify workspace paths for project discovery:
  npx tsx server/dev-server.ts /path/to/workspace1 /path/to/workspace2

Run the Vite dev server to view the UI:
  cd src/vscode-atopile/webviews && npm run dev
`);
});
