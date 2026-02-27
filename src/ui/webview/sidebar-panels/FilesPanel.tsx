import { useState, useCallback } from "react";
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
import { EmptyState, Spinner } from "../shared/components";
import { vscode } from "../shared/vscodeApi";
import { WebviewWebSocketClient } from "../shared/webviewWebSocketClient";
import type { FileNode } from "../../shared/types";
import "./FilesPanel.css";

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

interface TreeNodeProps {
  node: FileNode;
  path: string;
  depth: number;
  expandedDirs: Set<string>;
  onToggleDir: (path: string) => void;
  onOpenFile: (path: string) => void;
}

function TreeNode({
  node,
  path,
  depth,
  expandedDirs,
  onToggleDir,
  onOpenFile,
}: TreeNodeProps) {
  const isFolder = node.children != null;
  const isExpanded = expandedDirs.has(path);

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
    ? { icon: isExpanded ? FolderOpen : Folder, className: `folder-icon${isExpanded ? " expanded" : ""}` }
    : fileStyle(node.name);

  return (
    <div className="tree-node">
      <div className="tree-row" onClick={handleClick}>
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
          {node.children.map((child) => {
            const childPath = `${path}/${child.name}`;
            return (
              <TreeNode
                key={childPath}
                node={child}
                path={childPath}
                depth={depth + 1}
                expandedDirs={expandedDirs}
                onToggleDir={onToggleDir}
                onOpenFile={onOpenFile}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

export function FilesPanel({ projectRoot }: { projectRoot: string | null }) {
  const projectFiles = WebviewWebSocketClient.useSubscribe("projectFiles");

  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());

  const handleToggleDir = useCallback((path: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
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
      if (!projectRoot) return;
      const fullPath = `${projectRoot}/${relativePath}`;
      vscode.postMessage({ type: "openFile", path: fullPath });
    },
    [projectRoot],
  );

  if (!projectRoot) {
    return (
      <EmptyState
        icon={<Files size={24} />}
        title="No project selected"
        description="Select a project to browse files"
      />
    );
  }

  if (!projectFiles || projectFiles.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
        }}
      >
        <Spinner size={14} />
      </div>
    );
  }

  return (
    <div className="file-tree">
      {projectFiles.map((node) => (
        <TreeNode
          key={node.name}
          node={node}
          path={node.name}
          depth={0}
          expandedDirs={expandedDirs}
          onToggleDir={handleToggleDir}
          onOpenFile={handleOpenFile}
        />
      ))}
    </div>
  );
}
