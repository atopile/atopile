import { useCallback, useEffect, useState, type MouseEvent as ReactMouseEvent } from "react";
import {
  Files,
  ChevronRight,
  Folder,
  FolderOpen,
  File,
  FileText,
  FileCode,
  FileJson,
  CircuitBoard,
  FileArchive,
  FileCog,
  Hash,
  Code,
  FileSpreadsheet,
  Image,
  Terminal,
  GitBranch,
} from "lucide-react";
import { EmptyState, Button, Input } from "../shared/components";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import { createWebviewLogger } from "../shared/logger";
import type { FileNode } from "../../shared/generated-types";
import {
  normalizePath,
  joinPath,
  relativeToProject,
  parentRelativePath,
  basename,
  joinChildPath,
  validateName,
  ancestorPaths,
} from "../../shared/paths";
import "./FilesPanel.css";

const logger = createWebviewLogger("FilesPanel");

function fileStyle(name: string): { icon: typeof File; className: string } {
  const ext = name.includes(".") ? name.split(".").pop()?.toLowerCase() : "";
  switch (ext) {
    case "ato":
      return { icon: FileCode, className: "file-ato" };
    case "py":
    case "pyi":
      return { icon: FileCode, className: "file-py" };
    case "json":
      return { icon: FileJson, className: "file-json" };
    case "yaml":
    case "yml":
    case "toml":
      return { icon: FileCog, className: "file-config" };
    case "md":
    case "markdown":
    case "txt":
    case "rst":
      return { icon: FileText, className: "file-docs" };
    case "ts":
    case "tsx":
    case "js":
    case "jsx":
      return { icon: FileCode, className: "file-ts" };
    case "css":
    case "scss":
    case "less":
      return { icon: Hash, className: "file-css" };
    case "html":
    case "xml":
      return { icon: Code, className: "file-html" };
    case "pdf":
      return { icon: File, className: "file-pdf" };
    case "csv":
      return { icon: FileSpreadsheet, className: "file-csv" };
    case "kicad_pcb":
    case "kicad_sch":
    case "kicad_pro":
      return { icon: CircuitBoard, className: "file-kicad" };
    case "png":
    case "jpg":
    case "jpeg":
    case "gif":
    case "svg":
    case "ico":
      return { icon: Image, className: "file-image" };
    case "zip":
    case "tar":
    case "gz":
    case "7z":
      return { icon: FileArchive, className: "file-archive" };
    case "sh":
    case "bash":
    case "zsh":
      return { icon: Terminal, className: "file-shell" };
    case "gitignore":
    case "gitattributes":
      return { icon: GitBranch, className: "file-git" };
    default:
      return { icon: File, className: "file-default" };
  }
}

type ExplorerAction =
  | "open"
  | "new-file"
  | "new-folder"
  | "rename"
  | "duplicate"
  | "delete"
  | "reveal"
  | "terminal";

interface ContextMenuTarget {
  fullPath: string;
  relativePath: string;
  isFolder: boolean;
  isRoot: boolean;
  directoryPath: string;
}

interface ContextMenuState {
  x: number;
  y: number;
  target: ContextMenuTarget;
}

interface FileDialogState {
  kind: "text" | "confirm";
  action: "new-file" | "new-folder" | "rename" | "delete";
  title: string;
  message: string;
  confirmLabel: string;
  target: ContextMenuTarget;
  value: string;
  error: string | null;
}

interface TreeNodeProps {
  node: FileNode;
  path: string;
  projectRoot: string;
  depth: number;
  expandedDirs: Set<string>;
  activePath: string | null;
  onToggleDir: (path: string) => void;
  onOpenFile: (path: string) => void;
  onOpenContextMenu: (event: ReactMouseEvent, target: ContextMenuTarget) => void;
}


function contextMenuItems(target: ContextMenuTarget): { action: ExplorerAction; label: string }[] {
  if (target.isRoot) {
    return [
      { action: "new-file", label: "New File" },
      { action: "new-folder", label: "New Folder" },
      { action: "reveal", label: "Reveal in Finder/Explorer" },
      { action: "terminal", label: "Open in Terminal" },
    ];
  }
  if (target.isFolder) {
    return [
      { action: "new-file", label: "New File" },
      { action: "new-folder", label: "New Folder" },
      { action: "rename", label: "Rename" },
      { action: "duplicate", label: "Duplicate" },
      { action: "delete", label: "Delete" },
      { action: "reveal", label: "Reveal in Finder/Explorer" },
      { action: "terminal", label: "Open in Terminal" },
    ];
  }
  return [
    { action: "open", label: "Open" },
    { action: "rename", label: "Rename" },
    { action: "duplicate", label: "Duplicate" },
    { action: "delete", label: "Delete" },
    { action: "reveal", label: "Reveal in Finder/Explorer" },
    { action: "terminal", label: "Open in Terminal" },
  ];
}

function TreeNode({
  node,
  path,
  projectRoot,
  depth,
  expandedDirs,
  activePath,
  onToggleDir,
  onOpenFile,
  onOpenContextMenu,
}: TreeNodeProps) {
  const isFolder = node.children != null;
  const isExpanded = expandedDirs.has(path);
  const fullPath = joinPath(projectRoot, path);
  const rowTarget: ContextMenuTarget = {
    fullPath,
    relativePath: path,
    isFolder,
    isRoot: false,
    directoryPath: isFolder ? fullPath : joinPath(projectRoot, parentRelativePath(path)),
  };

  const handleClick = () => {
    if (isFolder) {
      onToggleDir(path);
    } else {
      onOpenFile(path);
    }
  };

  const indents = [];
  for (let i = 0; i < depth; i++) {
    indents.push(<span key={i} className="tree-indent" />);
  }

  const { icon: Icon, className: iconClass } = isFolder
    ? {
        icon: isExpanded ? FolderOpen : Folder,
        className: `folder-icon${isExpanded ? " expanded" : ""}`,
      }
    : fileStyle(node.name);

  return (
    <div className="tree-node">
      <div
        className={`tree-row${activePath === path ? " active" : ""}`}
        onClick={handleClick}
        onContextMenu={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onOpenContextMenu(event, rowTarget);
        }}
      >
        {indents}
        {isFolder ? (
          <span className={`tree-row-chevron${isExpanded ? " expanded" : ""}`}>
            <ChevronRight size={14} />
          </span>
        ) : (
          <span className="tree-row-chevron" />
        )}
        <span className={`tree-row-icon ${iconClass}`}>
          <Icon size={14} />
        </span>
        <span className="tree-row-name">{node.name}</span>
      </div>
      {isFolder && isExpanded && (
        <div>
          {node.children?.map((child) => {
            const childPath = `${path}/${child.name}`;
            return (
              <TreeNode
                key={childPath}
                node={child}
                path={childPath}
                projectRoot={projectRoot}
                depth={depth + 1}
                expandedDirs={expandedDirs}
                activePath={activePath}
                onToggleDir={onToggleDir}
                onOpenFile={onOpenFile}
                onOpenContextMenu={onOpenContextMenu}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

export function FilesPanel() {
  const projectState = WebviewRpcClient.useSubscribe("projectState");
  const { selectedProjectRoot: projectRoot, activeFilePath } = projectState;
  const projectFilesState = WebviewRpcClient.useSubscribe("projectFiles");
  const fileAction = WebviewRpcClient.useSubscribe("fileAction");

  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [dialog, setDialog] = useState<FileDialogState | null>(null);
  const projectFiles =
    projectFilesState.projectRoot === projectRoot ? projectFilesState.files : [];

  const activeRelativePath =
    projectRoot && activeFilePath ? relativeToProject(projectRoot, activeFilePath) : null;

  useEffect(() => {
    if (!activeRelativePath) {
      return;
    }
    setExpandedDirs((previous) => {
      const next = new Set(previous);
      let changed = false;
      for (const ancestor of ancestorPaths(activeRelativePath)) {
        if (!next.has(ancestor)) {
          next.add(ancestor);
          changed = true;
        }
      }
      return changed ? next : previous;
    });
  }, [activeRelativePath]);

  useEffect(() => {
    if (!contextMenu && !dialog) {
      return;
    }
    const handleMouseDown = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest(".file-tree-context-menu") || target?.closest(".file-tree-dialog")) {
        return;
      }
      setContextMenu(null);
      setDialog(null);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setContextMenu(null);
        setDialog(null);
      }
    };
    window.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [contextMenu, dialog]);

  const handleToggleDir = useCallback((path: string) => {
    setExpandedDirs((previous) => {
      const next = new Set(previous);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const handleOpenFile = useCallback(
    (relativePath: string) => {
      if (!projectRoot) {
        return;
      }
      logger.info(`openFile path=${relativePath}`);
      void rpcClient?.requestAction("vscode.openFile", { path: joinPath(projectRoot, relativePath) });
    },
    [projectRoot],
  );

  const revealPath = useCallback(
    (fullPath: string | null, includeSelf = false) => {
      if (!projectRoot || !fullPath) {
        return;
      }
      const relativePath = relativeToProject(projectRoot, fullPath);
      if (relativePath == null) {
        return;
      }
      setExpandedDirs((previous) => {
        const next = new Set(previous);
        for (const ancestor of ancestorPaths(relativePath)) {
          next.add(ancestor);
        }
        if (includeSelf && relativePath) {
          next.add(relativePath);
        }
        return next;
      });
    },
    [projectRoot],
  );

  useEffect(() => {
    if (!fileAction.path || fileAction.action === "delete") {
      return;
    }
    revealPath(fileAction.path, fileAction.isFolder);
    if (fileAction.action !== "create_file" || !projectRoot) {
      return;
    }
    const relativePath = relativeToProject(projectRoot, fileAction.path);
    if (relativePath) {
      handleOpenFile(relativePath);
    }
  }, [fileAction, handleOpenFile, projectRoot, revealPath]);

  const openContextMenu = useCallback(
    (event: ReactMouseEvent, target: ContextMenuTarget) => {
      const width = 210;
      const height = 260;
      setDialog(null);
      setContextMenu({
        x: Math.max(8, Math.min(event.clientX, window.innerWidth - width)),
        y: Math.max(8, Math.min(event.clientY, window.innerHeight - height)),
        target,
      });
    },
    [],
  );

  const executeAction = useCallback(
    async (action: ExplorerAction, target: ContextMenuTarget, value?: string) => {
      logger.info(
        `action=${action} target=${target.fullPath} folder=${target.isFolder} root=${target.isRoot}`,
      );
      switch (action) {
        case "open":
          if (!target.isFolder && target.relativePath) {
            handleOpenFile(target.relativePath);
          }
          return;

        case "new-file": {
          const path = joinChildPath(target.directoryPath, value ?? "");
          rpcClient?.sendAction("createFile", { path });
          logger.info(`createFile requested path=${path}`);
          return;
        }

        case "new-folder": {
          const path = joinChildPath(target.directoryPath, value ?? "");
          rpcClient?.sendAction("createFolder", { path });
          logger.info(`createFolder requested path=${path}`);
          return;
        }

        case "rename": {
          const newPath = joinChildPath(target.directoryPath, value ?? "");
          if (normalizePath(newPath) === normalizePath(target.fullPath)) {
            return;
          }
          rpcClient?.sendAction("renamePath", {
            path: target.fullPath,
            newPath,
          });
          logger.info(`renamePath requested target=${target.fullPath} next=${newPath}`);
          return;
        }

        case "duplicate": {
          rpcClient?.sendAction("duplicatePath", {
            path: target.fullPath,
          });
          logger.info(`duplicatePath requested target=${target.fullPath}`);
          return;
        }

        case "delete":
          rpcClient?.sendAction("deletePath", { path: target.fullPath });
          logger.info(`deletePath completed target=${target.fullPath}`);
          return;

        case "reveal":
          await rpcClient?.requestAction("vscode.revealInOs", { path: target.fullPath });
          logger.info(`revealInOs completed target=${target.fullPath}`);
          return;

        case "terminal":
          await rpcClient?.requestAction("vscode.openInTerminal", { path: target.fullPath });
          logger.info(`openInTerminal completed target=${target.fullPath}`);
          return;
      }
    },
    [handleOpenFile, projectRoot, revealPath],
  );

  const handleContextAction = useCallback(
    async (action: ExplorerAction, target: ContextMenuTarget) => {
      try {
        setContextMenu(null);
        switch (action) {
          case "new-file":
            setDialog({
              kind: "text",
              action,
              title: "New File",
              message: "Enter the file name.",
              confirmLabel: "Create",
              target,
              value: "",
              error: null,
            });
            return;

          case "new-folder":
            setDialog({
              kind: "text",
              action,
              title: "New Folder",
              message: "Enter the folder name.",
              confirmLabel: "Create",
              target,
              value: "",
              error: null,
            });
            return;

          case "rename":
            setDialog({
              kind: "text",
              action,
              title: `Rename ${target.isFolder ? "Folder" : "File"}`,
              message: target.fullPath,
              confirmLabel: "Rename",
              target,
              value: basename(target.fullPath),
              error: null,
            });
            return;

          case "delete":
            setDialog({
              kind: "confirm",
              action,
              title: `Delete ${target.isFolder ? "Folder" : "File"}`,
              message: `Delete "${basename(target.fullPath)}"?`,
              confirmLabel: "Delete",
              target,
              value: "",
              error: null,
            });
            return;

          default:
            await executeAction(action, target);
        }
      } catch (error) {
        logger.error(
          `action=${action} target=${target.fullPath} failed error=${error instanceof Error ? error.message : String(error)}`,
        );
        window.alert(error instanceof Error ? error.message : String(error));
      }
    },
    [executeAction],
  );

  const submitDialog = useCallback(async () => {
    if (!dialog) {
      return;
    }
    if (dialog.kind === "text") {
      const error = validateName(dialog.value);
      if (error) {
        setDialog({ ...dialog, error });
        return;
      }
    }

    try {
      await executeAction(dialog.action, dialog.target, dialog.value);
      setDialog(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      logger.error(
        `action=${dialog.action} target=${dialog.target.fullPath} failed error=${message}`,
      );
      setDialog({ ...dialog, error: message });
    }
  }, [dialog, executeAction]);

  if (!projectRoot) {
    return (
      <EmptyState
        icon={<Files size={24} />}
        title="No project selected"
        description="Select a project to browse files"
      />
    );
  }

  const rootTarget: ContextMenuTarget = {
    fullPath: projectRoot,
    relativePath: "",
    isFolder: true,
    isRoot: true,
    directoryPath: projectRoot,
  };

  if (projectFiles.length === 0) {
    return (
      <div className="file-tree-empty">
        <EmptyState
          icon={<Files size={24} />}
          title="No files yet"
          description="Create a file or folder in the selected project"
        />
        <div className="file-tree-empty-actions">
          <Button size="sm" variant="outline" onClick={() => void handleContextAction("new-file", rootTarget)}>
            New File
          </Button>
          <Button size="sm" variant="outline" onClick={() => void handleContextAction("new-folder", rootTarget)}>
            New Folder
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="file-tree"
      onContextMenu={(event) => {
        const target = event.target as HTMLElement | null;
        if (target?.closest(".tree-row")) {
          return;
        }
        event.preventDefault();
        openContextMenu(event, rootTarget);
      }}
    >
      {projectFiles.map((node) => (
        <TreeNode
          key={node.name}
          node={node}
          path={node.name}
          projectRoot={projectRoot}
          depth={0}
          expandedDirs={expandedDirs}
          activePath={activeRelativePath}
          onToggleDir={handleToggleDir}
          onOpenFile={handleOpenFile}
          onOpenContextMenu={openContextMenu}
        />
      ))}
      {contextMenu ? (
        <div
          className="file-tree-context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          {contextMenuItems(contextMenu.target).map((item) => (
            <button
              key={item.action}
              type="button"
              className="file-tree-context-item"
              onClick={() => void handleContextAction(item.action, contextMenu.target)}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
      {dialog ? (
        <div className="file-tree-dialog-backdrop">
          <div className="file-tree-dialog" role="dialog" aria-modal="true">
            <div className="file-tree-dialog-title">{dialog.title}</div>
            <div className="file-tree-dialog-message">{dialog.message}</div>
            {dialog.kind === "text" ? (
              <Input
                autoFocus
                value={dialog.value}
                onChange={(event) =>
                  setDialog((current) =>
                    current ? { ...current, value: event.target.value, error: null } : current,
                  )
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void submitDialog();
                  }
                }}
              />
            ) : null}
            {dialog.error ? <div className="file-tree-dialog-error">{dialog.error}</div> : null}
            <div className="file-tree-dialog-actions">
              <Button variant="outline" onClick={() => setDialog(null)}>
                Cancel
              </Button>
              <Button
                variant={dialog.action === "delete" ? "destructive" : "default"}
                onClick={() => void submitDialog()}
              >
                {dialog.confirmLabel}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
