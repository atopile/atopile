/**
 * FileExplorer - Displays project files in a compact card format.
 * Styled consistently with DependencyCard.
 */

import { useState, memo } from 'react';
import { ChevronDown, ChevronRight, Folder, FolderOpen, FileCode, FileText } from 'lucide-react';
import './FileExplorer.css';

// File tree node for file explorer
export interface FileTreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  extension?: string;  // 'ato' | 'py'
  children?: FileTreeNode[];
}

// File icon component
function getFileIcon(extension: string | undefined, size: number = 12) {
  switch (extension) {
    case 'ato':
      return <FileCode size={size} className="file-icon ato" />;
    case 'py':
      return <FileText size={size} className="file-icon python" />;
    default:
      return <FileText size={size} className="file-icon" />;
  }
}

// File tree node component - memoized for performance
const FileTreeNodeComponent = memo(function FileTreeNodeComponent({
  node,
  depth,
  onFileClick,
  defaultExpanded = false
}: {
  node: FileTreeNode;
  depth: number;
  onFileClick?: (path: string) => void;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const isFolder = node.type === 'folder';
  const hasChildren = isFolder && node.children && node.children.length > 0;

  return (
    <div className="file-tree-node">
      <div
        className={`file-tree-row ${isFolder ? 'folder' : 'file'} ${node.extension || ''}`}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
        onClick={(e) => {
          e.stopPropagation();  // Prevent bubbling to parent card
          if (isFolder) {
            setExpanded(!expanded);
          } else if (onFileClick) {
            onFileClick(node.path);
          }
        }}
      >
        {isFolder ? (
          <>
            <span className="file-tree-expand">
              {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </span>
            {expanded ? (
              <FolderOpen size={14} className="folder-icon open" />
            ) : (
              <Folder size={14} className="folder-icon" />
            )}
          </>
        ) : (
          <>
            <span className="file-tree-spacer" />
            {getFileIcon(node.extension, 14)}
          </>
        )}
        <span className="file-tree-name">{node.name}</span>
      </div>
      {expanded && hasChildren && (
        <div className="file-tree-children">
          {[...node.children!]
            .sort((a, b) => {
              // Files come before folders
              if (a.type === 'file' && b.type === 'folder') return -1;
              if (a.type === 'folder' && b.type === 'file') return 1;
              // Then alphabetically by name
              return a.name.localeCompare(b.name);
            })
            .map((child) => (
              <FileTreeNodeComponent
                key={child.path}
                node={child}
                depth={depth + 1}
                onFileClick={onFileClick}
                defaultExpanded={false}
              />
            ))}
        </div>
      )}
    </div>
  );
});

// Count total files recursively
function countFiles(nodes: FileTreeNode[]): number {
  let count = 0;
  for (const node of nodes) {
    if (node.type === 'file') {
      count++;
    } else if (node.children) {
      count += countFiles(node.children);
    }
  }
  return count;
}

interface FileExplorerProps {
  files: FileTreeNode[];
  onFileClick?: (path: string) => void;
}

export const FileExplorer = memo(function FileExplorer({
  files,
  onFileClick
}: FileExplorerProps) {
  const [expanded, setExpanded] = useState(false);

  if (!files || files.length === 0) {
    return null;
  }

  // Sort files before folders, then alphabetically
  const sortedFiles = [...files].sort((a, b) => {
    // Files come before folders
    if (a.type === 'file' && b.type === 'folder') return -1;
    if (a.type === 'folder' && b.type === 'file') return 1;
    // Then alphabetically by name
    return a.name.localeCompare(b.name);
  });

  const fileCount = countFiles(files);

  return (
    <div className="file-explorer-card" onClick={(e) => e.stopPropagation()}>
      <div
        className="file-explorer-card-header"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
      >
        <span className="file-explorer-card-expand">
          <ChevronDown
            size={12}
            className={`expand-icon ${expanded ? 'expanded' : ''}`}
          />
        </span>
        <Folder size={14} className="file-explorer-card-icon" />
        <span className="file-explorer-card-title">
          Files
        </span>
        <span className="file-count">{fileCount}</span>
      </div>

      {expanded && (
        <div className="file-explorer-card-content">
          {sortedFiles.map((node) => (
            <FileTreeNodeComponent
              key={node.path}
              node={node}
              depth={0}
              onFileClick={onFileClick}
              defaultExpanded={false}
            />
          ))}
        </div>
      )}
    </div>
  );
});
