/**
 * FileExplorerPanel - VSCode-style file explorer for the sidebar.
 *
 * Clones VSCode's native file explorer as closely as possible.
 */

import { useState, useCallback, useEffect, useMemo, useRef, memo } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  File,
  FileCode,
  FileText,
  FileJson,
  FileType,
  Settings,
  Hash,
  Code,
  Table,
  GitBranch,
  Image,
  FileArchive,
  Terminal,
  Search,
  X,
  FilePlus,
  FolderPlus,
  ChevronsDownUp,
  ArrowDownAZ,
  ArrowDownWideNarrow,
  Clock,
} from 'lucide-react';
import { useStore } from '../store';
import { postToExtension } from '../api/vscodeApi';
import { FileContextMenu, type ContextMenuPosition, type ContextMenuTarget } from './FileContextMenu';
import './FileExplorerPanel.css';

// ============================================================================
// Atopile Icon Component (same as header logo)
// ============================================================================

const AtopileIcon = memo(function AtopileIcon({ size = 16 }: { size?: number }) {
  // Try to use the same icon URL as the header if available
  const iconUrl =
    typeof window !== 'undefined'
      ? (window as Window & { __ATOPILE_ICON_URL__?: string }).__ATOPILE_ICON_URL__
      : undefined;

  if (iconUrl) {
    return (
      <img
        src={iconUrl}
        alt=""
        width={size}
        height={size}
        className="icon file-ato"
        style={{ objectFit: 'contain' }}
      />
    );
  }

  // Fallback: simplified orange "circuit" icon
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="icon file-ato"
    >
      {/* Simplified circuit-like atopile icon */}
      <rect x="1" y="1" width="4" height="4" rx="0.5" fill="#f95015" />
      <rect x="11" y="1" width="4" height="4" rx="0.5" fill="#f95015" />
      <rect x="1" y="11" width="4" height="4" rx="0.5" fill="#f95015" />
      <rect x="11" y="11" width="4" height="4" rx="0.5" fill="#f95015" />
      <rect x="6" y="6" width="4" height="4" rx="0.5" fill="#f95015" />
      <rect x="3" y="5" width="2" height="1" fill="#f95015" />
      <rect x="5" y="3" width="1" height="2" fill="#f95015" />
      <rect x="10" y="3" width="1" height="2" fill="#f95015" />
      <rect x="11" y="5" width="2" height="1" fill="#f95015" />
      <rect x="3" y="10" width="2" height="1" fill="#f95015" />
      <rect x="5" y="11" width="1" height="2" fill="#f95015" />
      <rect x="10" y="11" width="1" height="2" fill="#f95015" />
      <rect x="11" y="10" width="2" height="1" fill="#f95015" />
    </svg>
  );
});

// ============================================================================
// Types
// ============================================================================

export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
  mtime?: number; // Last modified timestamp
  lazyLoad?: boolean; // True if directory contents not yet loaded
}

export type SortMode = 'name' | 'modified' | 'type';

interface FileExplorerPanelProps {
  projectRoot: string | null;
}

// ============================================================================
// File Icon Component
// ============================================================================

const FileIcon = memo(function FileIcon({
  name,
  isDirectory,
  size = 16,
}: {
  name: string;
  isDirectory: boolean;
  isExpanded?: boolean;
  size?: number;
}) {
  // No icon for directories (cleaner look like Cursor)
  if (isDirectory) {
    return null;
  }

  // Get file extension
  const ext = name.includes('.') ? name.split('.').pop()?.toLowerCase() : '';

  // Map extensions to icons
  switch (ext) {
    // atopile - use the custom atopile logo
    case 'ato':
      return <AtopileIcon size={size} />;
    // Python
    case 'py':
    case 'pyi':
      return <FileCode size={size} className="icon file-python" />;
    // Config
    case 'json':
      return <FileJson size={size} className="icon file-json" />;
    case 'yaml':
    case 'yml':
      return <Settings size={size} className="icon file-yaml" />;
    case 'toml':
      return <Settings size={size} className="icon file-toml" />;
    // Docs
    case 'md':
    case 'markdown':
      return <FileText size={size} className="icon file-md" />;
    case 'txt':
    case 'rst':
      return <FileText size={size} className="icon file-text" />;
    // Web
    case 'ts':
    case 'tsx':
    case 'js':
    case 'jsx':
      return <FileCode size={size} className="icon file-ts" />;
    case 'css':
    case 'scss':
    case 'less':
      return <Hash size={size} className="icon file-css" />;
    case 'html':
      return <Code size={size} className="icon file-html" />;
    // Data
    case 'csv':
      return <Table size={size} className="icon file-csv" />;
    case 'xml':
      return <Code size={size} className="icon file-xml" />;
    // KiCad
    case 'kicad_pcb':
    case 'kicad_sch':
    case 'kicad_pro':
      return <FileType size={size} className="icon file-kicad" />;
    // Images
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'svg':
    case 'ico':
      return <Image size={size} className="icon file-image" />;
    // Archives
    case 'zip':
    case 'tar':
    case 'gz':
    case '7z':
      return <FileArchive size={size} className="icon file-archive" />;
    // Shell
    case 'sh':
    case 'bash':
    case 'zsh':
      return <Terminal size={size} className="icon file-shell" />;
    // Git
    case 'gitignore':
    case 'gitattributes':
      return <GitBranch size={size} className="icon file-git" />;
    // Default
    default:
      return <File size={size} className="icon file-default" />;
  }
});

// ============================================================================
// Tree Node Component
// ============================================================================

interface TreeNodeProps {
  node: FileNode;
  depth: number;
  selectedPaths: Set<string>;
  expandedPaths: Set<string>;
  projectRoot: string;
  renamingPath: string | null;
  draggedPath: string | null;
  dragOverPath: string | null;
  allPaths: string[]; // For shift-select range
  onSelect: (path: string, e: React.MouseEvent) => void;
  onToggle: (path: string) => void;
  onOpen: (path: string) => void;
  onContextMenu: (e: React.MouseEvent, node: FileNode) => void;
  onRename: (oldPath: string, newName: string) => void;
  onCancelRename: () => void;
  onDragStart: (path: string) => void;
  onDragEnd: () => void;
  onDragOver: (e: React.DragEvent, path: string, isDirectory: boolean) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent, targetPath: string) => void;
}

const TreeNode = memo(function TreeNode({
  node,
  depth,
  selectedPaths,
  expandedPaths,
  projectRoot,
  renamingPath,
  draggedPath,
  dragOverPath,
  allPaths,
  onSelect,
  onToggle,
  onOpen,
  onContextMenu,
  onRename,
  onCancelRename,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDragLeave,
  onDrop,
}: TreeNodeProps) {
  const isDirectory = node.type === 'directory';
  const isExpanded = expandedPaths.has(node.path);
  const isSelected = selectedPaths.has(node.path);
  const hasChildren = isDirectory && node.children && node.children.length > 0;
  const isRenaming = renamingPath === node.path;
  const isDragging = draggedPath === node.path;
  const isDragOver = dragOverPath === node.path && isDirectory;

  const [renameValue, setRenameValue] = useState(node.name);
  const renameInputRef = useRef<HTMLInputElement>(null);

  // Focus input when entering rename mode
  useEffect(() => {
    if (isRenaming && renameInputRef.current) {
      renameInputRef.current.focus();
      // Select the filename without extension
      const dotIndex = node.name.lastIndexOf('.');
      if (dotIndex > 0 && !isDirectory) {
        renameInputRef.current.setSelectionRange(0, dotIndex);
      } else {
        renameInputRef.current.select();
      }
    }
  }, [isRenaming, node.name, isDirectory]);

  // Reset rename value when node changes
  useEffect(() => {
    setRenameValue(node.name);
  }, [node.name]);

  // Indent: 16px for twistie + 8px per depth level
  const indent = 4 + depth * 16;

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (isRenaming) return; // Don't handle clicks while renaming
    onSelect(node.path, e);
    if (isDirectory) {
      onToggle(node.path);
    } else {
      // Single click opens files (only if not multi-selecting)
      if (!e.shiftKey && !e.metaKey && !e.ctrlKey) {
        onOpen(node.path);
      }
    }
  }, [node.path, isDirectory, isRenaming, onSelect, onToggle, onOpen]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (isRenaming) return; // Let input handle keys while renaming
    if (e.key === 'Enter') {
      if (isDirectory) {
        onToggle(node.path);
      } else {
        onOpen(node.path);
      }
    } else if (e.key === 'ArrowRight' && isDirectory && !isExpanded) {
      onToggle(node.path);
    } else if (e.key === 'ArrowLeft' && isDirectory && isExpanded) {
      onToggle(node.path);
    }
  }, [node.path, isDirectory, isExpanded, isRenaming, onToggle, onOpen]);

  const handleRenameKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (renameValue.trim() && renameValue !== node.name) {
        onRename(node.path, renameValue.trim());
      } else {
        onCancelRename();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setRenameValue(node.name);
      onCancelRename();
    }
  }, [node.path, node.name, renameValue, onRename, onCancelRename]);

  const handleRenameBlur = useCallback(() => {
    if (renameValue.trim() && renameValue !== node.name) {
      onRename(node.path, renameValue.trim());
    } else {
      onCancelRename();
    }
  }, [node.path, node.name, renameValue, onRename, onCancelRename]);

  // Sort children: directories first, then alphabetically
  const sortedChildren = useMemo(() => {
    if (!node.children) return [];
    return [...node.children].sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === 'directory' ? -1 : 1;
      }
      return a.name.localeCompare(b.name, undefined, { numeric: true });
    });
  }, [node.children]);

  const handleDragStart = useCallback((e: React.DragEvent) => {
    e.dataTransfer.setData('text/plain', node.path);
    // Set file URI for dropping into VS Code editor
    const fullPath = `${projectRoot}/${node.path}`;
    const fileUri = `file://${fullPath}`;
    e.dataTransfer.setData('text/uri-list', fileUri);
    e.dataTransfer.effectAllowed = 'copyMove';
    onDragStart(node.path);
  }, [node.path, projectRoot, onDragStart]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onDragOver(e, node.path, isDirectory);
  }, [node.path, isDirectory, onDragOver]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (isDirectory) {
      onDrop(e, node.path);
    }
  }, [node.path, isDirectory, onDrop]);

  return (
    <div className="tree-node" role="treeitem" aria-expanded={isDirectory ? isExpanded : undefined}>
      <div
        className={`tree-row ${isSelected ? 'selected' : ''} ${isDragging ? 'dragging' : ''} ${isDragOver ? 'drag-over' : ''}`}
        style={{ paddingLeft: `${indent}px` }}
        onClick={handleClick}
        onContextMenu={(e) => onContextMenu(e, node)}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="button"
        aria-label={node.name}
        draggable={!isRenaming}
        onDragStart={handleDragStart}
        onDragEnd={onDragEnd}
        onDragOver={handleDragOver}
        onDragLeave={onDragLeave}
        onDrop={handleDrop}
      >
        {/* Twistie (expand/collapse arrow) */}
        <span className={`twistie ${isDirectory && hasChildren ? '' : 'hidden'}`}>
          {isExpanded ? (
            <ChevronDown size={16} className="twistie-icon" />
          ) : (
            <ChevronRight size={16} className="twistie-icon" />
          )}
        </span>

        {/* File Icon (no icon for folders) */}
        {!isDirectory && (
          <span className="icon-container">
            <FileIcon name={node.name} isDirectory={isDirectory} />
          </span>
        )}

        {/* Name or Rename Input */}
        {isRenaming ? (
          <input
            ref={renameInputRef}
            type="text"
            className="tree-rename-input"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={handleRenameKeyDown}
            onBlur={handleRenameBlur}
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="tree-label">{node.name}</span>
        )}
      </div>

      {/* Children */}
      {isExpanded && hasChildren && (
        <div className="tree-children" role="group">
          {sortedChildren.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPaths={selectedPaths}
              expandedPaths={expandedPaths}
              projectRoot={projectRoot}
              renamingPath={renamingPath}
              draggedPath={draggedPath}
              dragOverPath={dragOverPath}
              allPaths={allPaths}
              onSelect={onSelect}
              onToggle={onToggle}
              onOpen={onOpen}
              onContextMenu={onContextMenu}
              onRename={onRename}
              onCancelRename={onCancelRename}
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
            />
          ))}
        </div>
      )}
    </div>
  );
});

// ============================================================================
// Main Component
// ============================================================================

export function FileExplorerPanel({ projectRoot }: FileExplorerPanelProps) {
  const projectFiles = useStore((s) => s.projectFiles);
  const isLoadingFiles = useStore((s) => s.isLoadingFiles);

  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [lastSelectedPath, setLastSelectedPath] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [renamingPath, setRenamingPath] = useState<string | null>(null);
  const [isRegexSearch, setIsRegexSearch] = useState(false);
  const [isCaseSensitive, setIsCaseSensitive] = useState(false);
  const [sortMode, setSortMode] = useState<SortMode>('name');
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Drag and drop state
  const [draggedPath, setDraggedPath] = useState<string | null>(null);
  const [dragOverPath, setDragOverPath] = useState<string | null>(null);
  const hoverExpandTimeout = useRef<number | null>(null);

  // Context menu state
  const [contextMenu, setContextMenu] = useState<{
    position: ContextMenuPosition;
    target: ContextMenuTarget;
  } | null>(null);

  // Get files for selected project
  const files = projectRoot ? projectFiles[projectRoot] : undefined;

  // Request files from the VS Code extension (not the backend)
  useEffect(() => {
    if (!projectRoot) return;
    if (files && files.length > 0) return; // Already have files

    useStore.getState().setLoadingFiles(true);
    // Send message to extension to list files
    postToExtension({
      type: 'listFiles',
      projectRoot,
      includeAll: true,
    });
  }, [projectRoot, files]);

  // Track directories currently being loaded
  const [loadingDirs, setLoadingDirs] = useState<Set<string>>(new Set());

  // Helper to update a specific directory's children in the file tree
  const updateDirectoryChildren = useCallback((
    nodes: FileNode[],
    targetPath: string,
    children: FileNode[]
  ): FileNode[] => {
    return nodes.map(node => {
      if (node.path === targetPath && node.type === 'directory') {
        return { ...node, children, lazyLoad: false };
      }
      if (node.children && node.type === 'directory') {
        return { ...node, children: updateDirectoryChildren(node.children, targetPath, children) };
      }
      return node;
    });
  }, []);

  // Listen for file system changes and file listing results from the extension
  useEffect(() => {
    if (!projectRoot) return;

    const handleMessage = (event: MessageEvent) => {
      const message = event.data;

      // Handle file listing response from extension
      if (message?.type === 'filesListed' && message.projectRoot === projectRoot) {
        useStore.getState().setProjectFiles(projectRoot, message.files || []);
        useStore.getState().setLoadingFiles(false);
        if (message.error) {
          console.error('Failed to list files:', message.error);
        }
      }

      // Handle lazy-loaded directory contents
      if (message?.type === 'directoryLoaded' && message.projectRoot === projectRoot) {
        const currentFiles = useStore.getState().projectFiles[projectRoot] || [];
        // Convert children to FileNode format (folder -> directory)
        const convertedChildren = (message.children || []).map((child: { name: string; path: string; type: string; extension?: string; children?: unknown[]; lazyLoad?: boolean }) => ({
          ...child,
          type: child.type === 'folder' ? 'directory' : 'file',
        })) as FileNode[];
        const updatedFiles = updateDirectoryChildren(currentFiles, message.directoryPath, convertedChildren);
        useStore.getState().setProjectFiles(projectRoot, updatedFiles);
        setLoadingDirs(prev => {
          const next = new Set(prev);
          next.delete(message.directoryPath);
          return next;
        });
        if (message.error) {
          console.error('Failed to load directory:', message.error);
        }
      }

      // Handle file system changes - clear files to trigger refresh
      if (message?.type === 'filesChanged' && message.projectRoot === projectRoot) {
        useStore.getState().setProjectFiles(projectRoot, []);
      }

      // When a file is duplicated, start rename mode on the new file
      if (message?.type === 'fileDuplicated' && message.newRelativePath) {
        // Small delay to let the file list refresh first
        setTimeout(() => {
          setRenamingPath(message.newRelativePath);
        }, 400);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [projectRoot, updateDirectoryChildren]);

  // Clean up drag state when drag ends anywhere (e.g., dropped outside, cancelled)
  useEffect(() => {
    const handleGlobalDragEnd = () => {
      setDraggedPath(null);
      setDragOverPath(null);
      if (hoverExpandTimeout.current) {
        clearTimeout(hoverExpandTimeout.current);
        hoverExpandTimeout.current = null;
      }
    };

    document.addEventListener('dragend', handleGlobalDragEnd);
    return () => document.removeEventListener('dragend', handleGlobalDragEnd);
  }, []);

  // Collapse all folders
  const handleCollapseAll = useCallback(() => {
    setExpandedPaths(new Set());
  }, []);

  // Cycle sort mode
  const handleCycleSort = useCallback(() => {
    setSortMode(prev => {
      if (prev === 'name') return 'modified';
      if (prev === 'modified') return 'type';
      return 'name';
    });
  }, []);

  // Handle expand/collapse
  const handleToggle = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  // Handle file open - paths are relative to project root
  const handleOpen = useCallback((path: string) => {
    if (!projectRoot) return;
    // Construct full path from project root + relative path
    const fullPath = `${projectRoot}/${path}`;
    // Send to VSCode extension to open the file
    postToExtension({ type: 'openSignals', openFile: fullPath });
  }, [projectRoot]);

  // Handle context menu (right-click)
  const handleContextMenu = useCallback((e: React.MouseEvent, node: FileNode) => {
    e.preventDefault();
    e.stopPropagation();
    if (!projectRoot) return;

    setContextMenu({
      position: { x: e.clientX, y: e.clientY },
      target: {
        path: `${projectRoot}/${node.path}`,
        relativePath: node.path,
        name: node.name,
        isDirectory: node.type === 'directory',
        projectRoot,
      },
    });
  }, [projectRoot]);

  // Close context menu
  const handleCloseContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  // Start renaming a file/folder
  const handleStartRename = useCallback((relativePath: string) => {
    setRenamingPath(relativePath);
  }, []);

  // Duplicate a file/folder - copy it and start rename on the copy
  const handleDuplicate = useCallback((relativePath: string) => {
    if (!projectRoot) return;

    const fullPath = `${projectRoot}/${relativePath}`;

    // Generate the new path with " copy" suffix
    const lastDot = relativePath.lastIndexOf('.');
    const lastSlash = relativePath.lastIndexOf('/');
    const isFile = lastDot > lastSlash;

    let newRelativePath: string;
    if (isFile) {
      // file.txt -> file copy.txt
      const baseName = relativePath.substring(0, lastDot);
      const ext = relativePath.substring(lastDot);
      newRelativePath = `${baseName} copy${ext}`;
    } else {
      // folder -> folder copy
      newRelativePath = `${relativePath} copy`;
    }

    const newFullPath = `${projectRoot}/${newRelativePath}`;

    // Send duplicate request to extension
    postToExtension({
      type: 'duplicateFile',
      sourcePath: fullPath,
      destPath: newFullPath,
      newRelativePath
    });
  }, [projectRoot]);

  // Handle rename completion
  const handleRename = useCallback((oldRelativePath: string, newName: string) => {
    if (!projectRoot) return;

    const oldFullPath = `${projectRoot}/${oldRelativePath}`;
    // Compute new path: replace the last segment with new name
    const parentPath = oldRelativePath.includes('/')
      ? oldRelativePath.substring(0, oldRelativePath.lastIndexOf('/'))
      : '';
    const newRelativePath = parentPath ? `${parentPath}/${newName}` : newName;
    const newFullPath = `${projectRoot}/${newRelativePath}`;

    // Send to extension to perform the rename
    postToExtension({ type: 'renameFile', oldPath: oldFullPath, newPath: newFullPath });

    // Clear renaming state
    setRenamingPath(null);

    // Refresh file list after a short delay to let the rename complete
    setTimeout(() => {
      // Clear cached files to force refresh
      useStore.getState().setProjectFiles(projectRoot, []);
    }, 200);
  }, [projectRoot]);

  // Cancel renaming
  const handleCancelRename = useCallback(() => {
    setRenamingPath(null);
  }, []);

  // Drag and drop handlers
  const handleDragStart = useCallback((path: string) => {
    setDraggedPath(path);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDraggedPath(null);
    setDragOverPath(null);
    if (hoverExpandTimeout.current) {
      clearTimeout(hoverExpandTimeout.current);
      hoverExpandTimeout.current = null;
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, path: string, isDirectory: boolean) => {
    // Only allow dropping on directories
    if (!isDirectory) {
      e.dataTransfer.dropEffect = 'none';
      return;
    }

    e.dataTransfer.dropEffect = 'move';
    setDragOverPath(path);

    // Clear previous timeout and set hover-to-expand
    if (hoverExpandTimeout.current) {
      clearTimeout(hoverExpandTimeout.current);
    }
    hoverExpandTimeout.current = window.setTimeout(() => {
      setExpandedPaths((prev) => {
        if (prev.has(path)) return prev;
        return new Set([...prev, path]);
      });
    }, 800);
  }, []);

  const handleDragLeave = useCallback(() => {
    // Don't clear immediately - let dragOver on new target handle it
    // This prevents flickering when moving between elements
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, targetPath: string) => {
    e.preventDefault();

    // Clean up drag state first
    const currentDraggedPath = draggedPath;
    setDraggedPath(null);
    setDragOverPath(null);
    if (hoverExpandTimeout.current) {
      clearTimeout(hoverExpandTimeout.current);
      hoverExpandTimeout.current = null;
    }

    if (!projectRoot || !currentDraggedPath) return;

    // Prevent dropping on self or into children
    if (currentDraggedPath === targetPath || targetPath.startsWith(currentDraggedPath + '/')) {
      return;
    }

    const sourceName = currentDraggedPath.split('/').pop() || '';
    if (!sourceName) return;

    const oldFullPath = `${projectRoot}/${currentDraggedPath}`;
    const newFullPath = `${projectRoot}/${targetPath}/${sourceName}`;

    // Send move request to extension
    postToExtension({ type: 'renameFile', oldPath: oldFullPath, newPath: newFullPath });

    // File watcher will handle the refresh
  }, [projectRoot, draggedPath]);

  // Create new file
  const handleCreateFile = useCallback(() => {
    if (!projectRoot) return;
    // Start renaming with a temporary new file entry
    // For now, send a message to create an untitled file
    postToExtension({ type: 'createFile', path: projectRoot });
  }, [projectRoot]);

  // Create new folder
  const handleCreateFolder = useCallback(() => {
    if (!projectRoot) return;
    postToExtension({ type: 'createFolder', path: projectRoot });
  }, [projectRoot]);


  // Handle keyboard events for the panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Get first selected path for rename operations
      const firstSelected = selectedPaths.size === 1 ? [...selectedPaths][0] : null;

      // Enter to start rename on selected item (only if single selection)
      if (e.key === 'Enter' && firstSelected && !renamingPath) {
        e.preventDefault();
        setRenamingPath(firstSelected);
      }
      // F2 to rename (Windows convention)
      if (e.key === 'F2' && firstSelected && !renamingPath) {
        e.preventDefault();
        setRenamingPath(firstSelected);
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('keydown', handleKeyDown);
      return () => container.removeEventListener('keydown', handleKeyDown);
    }
  }, [selectedPaths, renamingPath]);

  // Convert flat FileTreeNode[] to nested FileNode structure
  const fileTree = useMemo(() => {
    if (!files || files.length === 0) return [];

    // The store already has FileTreeNode[] which matches our FileNode interface
    // Just need to map type names
    const mapNode = (node: typeof files[0]): FileNode => ({
      name: node.name,
      path: node.path,
      type: node.type === 'folder' ? 'directory' : 'file',
      children: node.children?.map(mapNode),
    });

    return files.map(mapNode);
  }, [files]);

  // Filter tree by search query with regex and case sensitivity support
  const filteredTree = useMemo(() => {
    if (!searchQuery.trim()) return fileTree;

    // Build the matcher function based on settings
    let matcher: (name: string) => boolean;

    if (isRegexSearch) {
      try {
        const flags = isCaseSensitive ? '' : 'i';
        const regex = new RegExp(searchQuery, flags);
        matcher = (name: string) => regex.test(name);
      } catch {
        // Invalid regex - fall back to literal match
        matcher = isCaseSensitive
          ? (name: string) => name.includes(searchQuery)
          : (name: string) => name.toLowerCase().includes(searchQuery.toLowerCase());
      }
    } else {
      matcher = isCaseSensitive
        ? (name: string) => name.includes(searchQuery)
        : (name: string) => name.toLowerCase().includes(searchQuery.toLowerCase());
    }

    // Recursively filter nodes - keep a node if:
    // 1. Its name matches the query, OR
    // 2. Any of its children match (for directories)
    const filterNode = (node: FileNode): FileNode | null => {
      const nameMatches = matcher(node.name);

      if (node.type === 'directory' && node.children) {
        const filteredChildren = node.children
          .map(filterNode)
          .filter((n): n is FileNode => n !== null);

        // Keep directory if it has matching children or its name matches
        if (filteredChildren.length > 0 || nameMatches) {
          return {
            ...node,
            children: filteredChildren.length > 0 ? filteredChildren : node.children,
          };
        }
        return null;
      }

      // For files, only keep if name matches
      return nameMatches ? node : null;
    };

    return fileTree.map(filterNode).filter((n): n is FileNode => n !== null);
  }, [fileTree, searchQuery, isRegexSearch, isCaseSensitive]);

  // Sort nodes based on sort mode
  const sortedTree = useMemo(() => {
    const getExtension = (name: string) => {
      const idx = name.lastIndexOf('.');
      return idx > 0 ? name.substring(idx + 1).toLowerCase() : '';
    };

    const sortNodes = (nodes: FileNode[]): FileNode[] => {
      return [...nodes].sort((a, b) => {
        // Directories always first
        if (a.type !== b.type) {
          return a.type === 'directory' ? -1 : 1;
        }

        // Then sort by selected mode
        switch (sortMode) {
          case 'modified':
            // Sort by mtime descending (newest first), fall back to name
            if (a.mtime && b.mtime) {
              return b.mtime - a.mtime;
            }
            return a.name.localeCompare(b.name, undefined, { numeric: true });
          case 'type':
            // Sort by extension, then name
            const extA = getExtension(a.name);
            const extB = getExtension(b.name);
            if (extA !== extB) {
              return extA.localeCompare(extB);
            }
            return a.name.localeCompare(b.name, undefined, { numeric: true });
          case 'name':
          default:
            return a.name.localeCompare(b.name, undefined, { numeric: true });
        }
      }).map(node => ({
        ...node,
        children: node.children ? sortNodes(node.children) : undefined
      }));
    };
    return sortNodes(filteredTree);
  }, [filteredTree, sortMode]);

  // Collect all visible paths in order (for shift-select)
  const allVisiblePaths = useMemo(() => {
    const paths: string[] = [];
    const collectPaths = (nodes: FileNode[]) => {
      for (const node of nodes) {
        paths.push(node.path);
        if (node.type === 'directory' && expandedPaths.has(node.path) && node.children) {
          collectPaths(node.children);
        }
      }
    };
    collectPaths(sortedTree);
    return paths;
  }, [sortedTree, expandedPaths]);

  // Handle selection with multi-select support
  const handleSelect = useCallback((path: string, e: React.MouseEvent) => {
    if (e.shiftKey && lastSelectedPath) {
      // Shift+click: select range
      const startIdx = allVisiblePaths.indexOf(lastSelectedPath);
      const endIdx = allVisiblePaths.indexOf(path);
      if (startIdx !== -1 && endIdx !== -1) {
        const [from, to] = startIdx < endIdx ? [startIdx, endIdx] : [endIdx, startIdx];
        const rangePaths = allVisiblePaths.slice(from, to + 1);
        setSelectedPaths(new Set(rangePaths));
      }
    } else if (e.metaKey || e.ctrlKey) {
      // Cmd/Ctrl+click: toggle selection
      setSelectedPaths(prev => {
        const next = new Set(prev);
        if (next.has(path)) {
          next.delete(path);
        } else {
          next.add(path);
        }
        return next;
      });
      setLastSelectedPath(path);
    } else {
      // Normal click: single selection
      setSelectedPaths(new Set([path]));
      setLastSelectedPath(path);
    }
  }, [lastSelectedPath, allVisiblePaths]);

  // Auto-expand all folders when searching
  useEffect(() => {
    if (searchQuery.trim()) {
      // Collect all directory paths from filtered tree
      const collectDirPaths = (nodes: FileNode[]): string[] => {
        const paths: string[] = [];
        for (const node of nodes) {
          if (node.type === 'directory') {
            paths.push(node.path);
            if (node.children) {
              paths.push(...collectDirPaths(node.children));
            }
          }
        }
        return paths;
      };
      setExpandedPaths(new Set(collectDirPaths(filteredTree)));
    }
  }, [searchQuery, filteredTree]);

  // No project selected
  if (!projectRoot) {
    return (
      <div className="file-explorer-panel empty">
        <div className="empty-message">
          <Folder size={32} className="empty-icon" />
          <span>Select a project to view files</span>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoadingFiles && !files) {
    return (
      <div className="file-explorer-panel loading">
        <div className="loading-spinner" />
        <span>Loading files...</span>
      </div>
    );
  }

  // Empty project
  if (!files || files.length === 0) {
    return (
      <div className="file-explorer-panel empty">
        <div className="empty-message">
          <Folder size={32} className="empty-icon" />
          <span>No files found</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="file-explorer-panel"
      ref={containerRef}
      role="tree"
      aria-label="File Explorer"
    >
      {/* Header with actions */}
      <div className="file-explorer-header">
        <span className="file-explorer-title">Explorer</span>
        <div className="file-explorer-actions">
          <button
            className="file-explorer-action-btn"
            onClick={handleCreateFile}
            title="New File"
          >
            <FilePlus size={16} />
          </button>
          <button
            className="file-explorer-action-btn"
            onClick={handleCreateFolder}
            title="New Folder"
          >
            <FolderPlus size={16} />
          </button>
          <button
            className="file-explorer-action-btn"
            onClick={handleCollapseAll}
            title="Collapse All"
          >
            <ChevronsDownUp size={16} />
          </button>
          <button
            className={`file-explorer-action-btn ${sortMode !== 'name' ? 'active' : ''}`}
            onClick={handleCycleSort}
            title={`Sort by: ${sortMode === 'name' ? 'Name' : sortMode === 'modified' ? 'Date Modified' : 'Type'}`}
          >
            {sortMode === 'name' && <ArrowDownAZ size={16} />}
            {sortMode === 'modified' && <Clock size={16} />}
            {sortMode === 'type' && <ArrowDownWideNarrow size={16} />}
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="file-explorer-search-bar">
        <Search size={14} />
        <input
          ref={searchInputRef}
          type="text"
          placeholder="Search files..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button
          className={`search-option-btn ${isCaseSensitive ? 'active' : ''}`}
          onClick={() => setIsCaseSensitive(!isCaseSensitive)}
          title="Match Case"
        >
          Aa
        </button>
        <button
          className={`search-option-btn ${isRegexSearch ? 'active' : ''}`}
          onClick={() => setIsRegexSearch(!isRegexSearch)}
          title="Use Regular Expression"
        >
          .*
        </button>
        {searchQuery && (
          <button
            className="search-clear-btn"
            onClick={() => setSearchQuery('')}
            title="Clear search"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Tree Container */}
      <div className="tree-container">
        {sortedTree.length === 0 && searchQuery ? (
          <div className="no-results">
            <span>No files matching "{searchQuery}"</span>
          </div>
        ) : (
          sortedTree.map((node) => (
            <TreeNode
              key={node.path}
              node={node}
              depth={0}
              selectedPaths={selectedPaths}
              expandedPaths={expandedPaths}
              projectRoot={projectRoot}
              renamingPath={renamingPath}
              draggedPath={draggedPath}
              dragOverPath={dragOverPath}
              allPaths={allVisiblePaths}
              onSelect={handleSelect}
              onToggle={handleToggle}
              onOpen={handleOpen}
              onContextMenu={handleContextMenu}
              onRename={handleRename}
              onCancelRename={handleCancelRename}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            />
          ))
        )}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <FileContextMenu
          position={contextMenu.position}
          target={contextMenu.target}
          onClose={handleCloseContextMenu}
          onStartRename={handleStartRename}
          onDuplicate={handleDuplicate}
        />
      )}
    </div>
  );
}

export default FileExplorerPanel;
