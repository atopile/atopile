/**
 * Settings handlers for the sidebar webview.
 *
 * Handles atopile settings sync and browse dialog operations.
 */

import * as vscode from 'vscode';
import { backendServer } from '../../common/backendServer';
import { traceInfo, traceError } from '../../common/log/logging';
import { getWorkspaceSettings } from '../../common/settings';
import { getProjectRoot } from '../../common/utilities';
import type { AtopileSettingsMessage } from './types';

export interface SidebarSettingsHandlersOptions {
  postToWebview: (msg: Record<string, unknown>) => void;
}

export class SidebarSettingsHandlers {
  private readonly _postToWebview: (msg: Record<string, unknown>) => void;
  private _lastAtopileSettingsKey: string | null = null;

  constructor(opts: SidebarSettingsHandlersOptions) {
    this._postToWebview = opts.postToWebview;
  }

  /**
   * Send current atopile settings to the webview.
   * Used to initialize the toggle state correctly.
   */
  async sendAtopileSettings(): Promise<void> {
    try {
      const projectRoot = await getProjectRoot();
      const settings = await getWorkspaceSettings(projectRoot);
      traceInfo(`[SidebarSettings] Sending atopile settings: ato=${settings.ato}, from=${settings.from}`);
      this._postToWebview({
        type: 'atopileSettingsResponse',
        settings: {
          atoPath: settings.ato || null,
          fromSpec: settings.from || null,
        },
      });
    } catch (error) {
      traceError(`[SidebarSettings] Error getting atopile settings: ${error}`);
      this._postToWebview({
        type: 'atopileSettingsResponse',
        settings: {
          atoPath: null,
          fromSpec: null,
        },
      });
    }
  }

  /**
   * Handle atopile settings changes from the UI.
   * Syncs atopile settings to VS Code configuration.
   * Note: Does NOT restart the server - user must click the restart button.
   */
  async handleAtopileSettings(atopile: AtopileSettingsMessage['atopile']): Promise<void> {
    if (!atopile) return;

    traceInfo(`[SidebarSettings] handleAtopileSettings received: ${JSON.stringify(atopile)}`);

    // Build a key for comparison to avoid unnecessary updates
    const settingsKey = JSON.stringify({
      source: atopile.source,
      localPath: atopile.localPath,
    });

    // Skip if nothing changed - this is called on every state update
    if (settingsKey === this._lastAtopileSettingsKey) {
      traceInfo(`[SidebarSettings] Skipping - settings unchanged: ${settingsKey}`);
      return;
    }

    traceInfo(`[SidebarSettings] Processing new settings: ${settingsKey}`);
    this._lastAtopileSettingsKey = settingsKey;

    const config = vscode.workspace.getConfiguration('atopile');
    const hasWorkspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0;
    const target = hasWorkspace ? vscode.ConfigurationTarget.Workspace : vscode.ConfigurationTarget.Global;

    try {
      // Only manage atopile.ato setting - atopile.from is only set manually in settings
      if (atopile.source === 'local' && atopile.localPath) {
        traceInfo(`[SidebarSettings] Setting atopile.ato = ${atopile.localPath}`);
        await config.update('ato', atopile.localPath, target);
      } else {
        traceInfo(`[SidebarSettings] Clearing atopile.ato (using default)`);
        await config.update('ato', undefined, target);
      }
      traceInfo(`[SidebarSettings] Atopile settings saved. User must restart to apply.`);
    } catch (error) {
      traceError(`[SidebarSettings] Failed to update atopile settings: ${error}`);

      // Notify UI of the error
      backendServer.sendToWebview({
        type: 'atopileInstallError',
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  async browseAtopilePath(): Promise<void> {
    traceInfo('[SidebarSettings] Browsing for local atopile path');

    const result = await vscode.window.showOpenDialog({
      canSelectFiles: true,
      canSelectFolders: false,
      canSelectMany: false,
      openLabel: 'Select atopile binary',
      title: 'Select atopile binary',
      filters: process.platform === 'win32'
        ? { 'Executables': ['exe', 'cmd'], 'All files': ['*'] }
        : undefined,
    });

    const selectedPath = result?.[0]?.fsPath ?? null;
    traceInfo(`[SidebarSettings] Browse result: ${selectedPath}`);

    this._postToWebview({
      type: 'browseAtopilePathResult',
      path: selectedPath,
    });
  }

  async browseProjectPath(): Promise<void> {
    traceInfo('[SidebarSettings] Browsing for project directory');

    const defaultUri = vscode.workspace.workspaceFolders?.[0]?.uri;

    const result = await vscode.window.showOpenDialog({
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      defaultUri,
      openLabel: 'Select folder',
      title: 'Select project directory',
    });

    const selectedPath = result?.[0]?.fsPath ?? null;
    traceInfo(`[SidebarSettings] Browse project path result: ${selectedPath}`);

    this._postToWebview({
      type: 'browseProjectPathResult',
      path: selectedPath,
    });
  }

  async browseExportDirectory(): Promise<void> {
    traceInfo('[SidebarSettings] Browsing for export directory');

    const defaultUri = vscode.workspace.workspaceFolders?.[0]?.uri;

    const result = await vscode.window.showOpenDialog({
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      defaultUri,
      openLabel: 'Select export folder',
      title: 'Select export directory for manufacturing files',
    });

    const selectedPath = result?.[0]?.fsPath ?? null;
    traceInfo(`[SidebarSettings] Browse export directory result: ${selectedPath}`);

    this._postToWebview({
      type: 'browseExportDirectoryResult',
      path: selectedPath,
    });
  }
}
