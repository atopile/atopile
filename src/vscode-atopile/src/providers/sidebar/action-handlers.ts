/**
 * Action handlers for the sidebar webview.
 *
 * Handles open signals, file/layout/3D preview opening,
 * and project selection changes.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { backendServer } from '../../common/backendServer';
import { traceInfo, traceError } from '../../common/log/logging';
import { openPcb } from '../../common/kicad';
import { prepareThreeDViewer, handleThreeDModelBuildResult } from '../../common/3dmodel';
import { isModelViewerOpen, openModelViewerPreview } from '../../ui/modelviewer';
import { getBuildTarget, setProjectRoot, setSelectedTargets } from '../../common/target';
import { type Build, loadBuilds, getBuilds } from '../../common/manifest';
import { openLayoutEditor } from '../../ui/layout-editor';
import type { OpenSignalsMessage, SelectionChangedMessage } from './types';

export interface SidebarActionHandlersOptions {
  onProjectSelected?: (root: string | null) => void;
}

export class SidebarActionHandlers {
  private readonly _onProjectSelected?: (root: string | null) => void;

  constructor(opts: SidebarActionHandlersOptions) {
    this._onProjectSelected = opts.onProjectSelected;
  }

  handleOpenSignals(msg: OpenSignalsMessage): void {
    if (msg.openFile) {
      this.openFile(msg.openFile, msg.openFileLine ?? undefined, msg.openFileColumn ?? undefined);
    }
    if (msg.openLayout) {
      this.openLayoutPreview(msg.openLayout);
    }
    if (msg.openKicad) {
      this.openWithKicad(msg.openKicad);
    }
    if (msg.open3d) {
      void this.open3dPreview(msg.open3d);
    }
  }

  openFile(filePath: string, line?: number, column?: number): void {
    traceInfo(`[SidebarActions] Opening file: ${filePath}${line ? `:${line}` : ''}`);
    const uri = vscode.Uri.file(filePath);
    vscode.workspace.openTextDocument(uri).then(
      (doc) => {
        const options: vscode.TextDocumentShowOptions = {};
        if (line != null) {
          const position = new vscode.Position(Math.max(0, line - 1), column ?? 0);
          options.selection = new vscode.Range(position, position);
        }
        vscode.window.showTextDocument(doc, options);
      },
      (err) => {
        traceError(`[SidebarActions] Failed to open file ${filePath}: ${err}`);
      }
    );
  }

  openLayoutPreview(_filePath: string): void {
    // The server already loaded the PCB via the openLayout action.
    // Just open the editor webview.
    void openLayoutEditor();
  }

  openWithKicad(filePath: string): void {
    const pcbPath = this._resolveFilePath(filePath, '.kicad_pcb');
    if (!pcbPath) {
      traceError(`[SidebarActions] KiCad layout file not found: ${filePath}`);
      vscode.window.showErrorMessage('KiCad layout file not found. Run a build to generate it.');
      return;
    }

    const isWebIde =
      vscode.env.uiKind === vscode.UIKind.Web ||
      process.env.WEB_IDE_MODE === '1' ||
      Boolean(process.env.OPENVSCODE_SERVER_ROOT);

    if (isWebIde) {
      vscode.window.showInformationMessage('KiCad is unavailable in web-ide. Use the Layout action instead.');
    } else {
      void openPcb(pcbPath).catch((error) => {
        traceError(`[SidebarActions] Failed to open KiCad: ${error}`);
        vscode.window.showErrorMessage(`Failed to open KiCad: ${error instanceof Error ? error.message : error}`);
      });
    }
  }

  async open3dPreview(filePath: string): Promise<void> {
    await loadBuilds();

    const modelPath = this._resolveFilePath(filePath, '.glb') ?? filePath;
    const build = this._resolveBuildFor3dModel(modelPath);
    if (!build?.root || !build.name) {
      traceError('[SidebarActions] No build target selected for 3D export.');
      await openModelViewerPreview();
      return;
    }

    // Keep extension target selection aligned with actions triggered from the web UI.
    setSelectedTargets([build]);

    const glbPath = modelPath.toLowerCase().endsWith('.glb') ? modelPath : build.model_path;

    prepareThreeDViewer(glbPath, () => {
      backendServer.sendToWebview({
        type: 'triggerBuild',
        projectRoot: build.root,
        targets: [build.name],
        includeTargets: ['glb-only'],
        excludeTargets: ['default'],
      });
    });

    await openModelViewerPreview();
  }

  handleThreeDModelBuildResult(success: boolean, error?: string | null): void {
    traceInfo(`[SidebarActions] Received threeDModelBuildResult: success=${success}, error="${error}"`);
    handleThreeDModelBuildResult(success, error);
  }

  async handleSelectionChanged(message: SelectionChangedMessage): Promise<void> {
    const projectRoot = message.projectRoot ?? null;
    setProjectRoot(projectRoot ?? undefined);

    // Notify the file watcher about project selection changes
    this._onProjectSelected?.(projectRoot);

    await loadBuilds();
    const builds = getBuilds();
    const projectBuilds = projectRoot ? builds.filter((build) => build.root === projectRoot) : [];
    const selectedBuilds = message.targetNames.length
      ? projectBuilds.filter((build) => message.targetNames.includes(build.name))
      : [];
    setSelectedTargets(selectedBuilds);

    // If the 3D model viewer is open, prepare viewer for the new target
    if (isModelViewerOpen() && selectedBuilds.length > 0) {
      const build = selectedBuilds[0];
      if (build?.root && build?.name && build?.model_path) {
        traceInfo(`[SidebarActions] 3D viewer open, preparing viewer for new target: ${build.name}`);

        prepareThreeDViewer(build.model_path, () => {
          backendServer.sendToWebview({
            type: 'triggerBuild',
            projectRoot: build.root,
            targets: [build.name],
            includeTargets: ['glb-only'],
            excludeTargets: ['default'],
          });
        });

        await openModelViewerPreview();
      }
    }
  }

  // --- Private helpers ---

  private _findFirstFileByExt(dirPath: string, ext: string): string | null {
    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isFile() && entry.name.toLowerCase().endsWith(ext)) {
          return path.join(dirPath, entry.name);
        }
      }
    } catch (error) {
      traceError(`[SidebarActions] Failed to read directory ${dirPath}: ${error}`);
    }
    return null;
  }

  private _resolveFilePath(filePath: string, ext: string): string | null {
    if (!fs.existsSync(filePath)) {
      return null;
    }
    try {
      const stat = fs.statSync(filePath);
      if (stat.isFile()) {
        return filePath.toLowerCase().endsWith(ext) ? filePath : null;
      }
      if (stat.isDirectory()) {
        return this._findFirstFileByExt(filePath, ext);
      }
    } catch (error) {
      traceError(`[SidebarActions] Failed to stat ${filePath}: ${error}`);
    }
    return null;
  }

  private _resolveBuildFor3dModel(modelPath: string): Build | undefined {
    const selected = getBuildTarget();
    if (selected?.root && selected.name) {
      return selected;
    }

    const resolvedModelPath = path.resolve(modelPath);
    const builds = getBuilds();

    const byExactModelPath = builds.find(
      (build) => path.resolve(build.model_path) === resolvedModelPath
    );
    if (byExactModelPath) {
      return byExactModelPath;
    }

    for (const build of builds) {
      const buildDir = path.resolve(build.root, 'build', 'builds', build.name) + path.sep;
      if (resolvedModelPath.startsWith(buildDir)) {
        return build;
      }
    }

    const marker = `${path.sep}build${path.sep}builds${path.sep}`;
    const markerIndex = resolvedModelPath.lastIndexOf(marker);
    if (markerIndex !== -1) {
      const inferredRoot = resolvedModelPath.slice(0, markerIndex);
      const remaining = resolvedModelPath.slice(markerIndex + marker.length);
      const [targetName] = remaining.split(path.sep);

      if (targetName) {
        const fromManifest = builds.find(
          (build) =>
            build.name === targetName &&
            path.resolve(build.root) === path.resolve(inferredRoot)
        );
        if (fromManifest) {
          return fromManifest;
        }

        traceInfo(`[SidebarActions] Inferred 3D target from path: ${targetName}`);
        return {
          name: targetName,
          entry: '',
          pcb_path: '',
          model_path: path.join(
            inferredRoot,
            'build',
            'builds',
            targetName,
            `${targetName}.pcba.glb`
          ),
          root: inferredRoot,
        };
      }
    }

    return undefined;
  }
}
