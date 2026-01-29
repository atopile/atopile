/**
 * FileContextMenu - Context menu for file explorer items.
 *
 * Provides essential right-click operations.
 */

import { useEffect, useRef, useCallback } from 'react';
import { FolderOpen, Copy, Pencil, Trash2, Files, Terminal, FileCode } from 'lucide-react';
import { postToExtension } from '../api/vscodeApi';
import './FileContextMenu.css';

export interface ContextMenuPosition {
  x: number;
  y: number;
}

export interface ContextMenuTarget {
  path: string;          // Full path to file/folder
  relativePath: string;  // Relative path from project root
  name: string;
  isDirectory: boolean;
  projectRoot: string;
}

interface FileContextMenuProps {
  position: ContextMenuPosition;
  target: ContextMenuTarget;
  onClose: () => void;
  onStartRename: (relativePath: string) => void;
  onDuplicate: (relativePath: string) => void;
}

interface MenuItem {
  label: string;
  icon?: React.ReactNode;
  shortcut?: string;
  onClick: () => void;
  isDanger?: boolean;
}

export function FileContextMenu({ position, target, onClose, onStartRename, onDuplicate }: FileContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    // Small delay to prevent immediate close from the right-click event
    const timeoutId = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscape);
    }, 0);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  // Adjust position to stay within viewport
  useEffect(() => {
    if (!menuRef.current) return;

    const menu = menuRef.current;
    const rect = menu.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let adjustedX = position.x;
    let adjustedY = position.y;

    // Adjust horizontal position
    if (position.x + rect.width > viewportWidth) {
      adjustedX = viewportWidth - rect.width - 8;
    }

    // Adjust vertical position
    if (position.y + rect.height > viewportHeight) {
      adjustedY = viewportHeight - rect.height - 8;
    }

    menu.style.left = `${adjustedX}px`;
    menu.style.top = `${adjustedY}px`;
  }, [position]);

  // Action handlers
  const handleRevealInFinder = useCallback(() => {
    postToExtension({ type: 'revealInFinder', path: target.path });
    onClose();
  }, [target.path, onClose]);

  const handleCopyPath = useCallback(() => {
    navigator.clipboard.writeText(target.path);
    onClose();
  }, [target.path, onClose]);

  const handleCopyRelativePath = useCallback(() => {
    navigator.clipboard.writeText(target.relativePath);
    onClose();
  }, [target.relativePath, onClose]);

  const handleRename = useCallback(() => {
    onStartRename(target.relativePath);
    onClose();
  }, [target.relativePath, onStartRename, onClose]);

  const handleDelete = useCallback(() => {
    postToExtension({ type: 'deleteFile', path: target.path });
    onClose();
  }, [target.path, onClose]);

  const handleDuplicate = useCallback(() => {
    onDuplicate(target.relativePath);
    onClose();
  }, [target.relativePath, onDuplicate, onClose]);

  const handleOpenInTerminal = useCallback(() => {
    // For files, open terminal in parent directory
    const terminalPath = target.isDirectory ? target.path : target.path.substring(0, target.path.lastIndexOf('/'));
    postToExtension({ type: 'openInTerminal', path: terminalPath });
    onClose();
  }, [target.path, target.isDirectory, onClose]);

  const handleCopyAsImport = useCallback(() => {
    const ext = target.name.split('.').pop()?.toLowerCase() || '';
    let importStatement = '';

    // Generate import based on file type
    if (ext === 'py' || ext === 'pyi') {
      // Python: from path.to.module import module
      const modulePath = target.relativePath.replace(/\.pyi?$/, '').replace(/\//g, '.');
      const moduleName = target.name.replace(/\.pyi?$/, '');
      importStatement = `from ${modulePath.replace(`.${moduleName}`, '')} import ${moduleName}`;
    } else if (ext === 'ts' || ext === 'tsx' || ext === 'js' || ext === 'jsx') {
      // TypeScript/JavaScript
      const importPath = './' + target.relativePath.replace(/\.(tsx?|jsx?)$/, '');
      const moduleName = target.name.replace(/\.(tsx?|jsx?)$/, '');
      importStatement = `import { ${moduleName} } from '${importPath}';`;
    } else if (ext === 'ato') {
      // atopile: from "path/to/file.ato" import ModuleName
      const moduleName = target.name.replace(/\.ato$/, '');
      importStatement = `from "${target.relativePath}" import ${moduleName}`;
    } else {
      // Default: just copy path
      importStatement = target.relativePath;
    }

    navigator.clipboard.writeText(importStatement);
    onClose();
  }, [target.name, target.relativePath, onClose]);

  const isMac = typeof navigator !== 'undefined' && navigator.platform.includes('Mac');
  const canCopyAsImport = ['py', 'pyi', 'ts', 'tsx', 'js', 'jsx', 'ato'].includes(
    target.name.split('.').pop()?.toLowerCase() || ''
  );

  const menuItems: MenuItem[] = [
    {
      label: isMac ? 'Reveal in Finder' : 'Reveal in Explorer',
      icon: <FolderOpen size={14} />,
      shortcut: isMac ? '⌥⌘R' : 'Shift+Alt+R',
      onClick: handleRevealInFinder,
    },
    {
      label: 'Open in Terminal',
      icon: <Terminal size={14} />,
      onClick: handleOpenInTerminal,
    },
    {
      label: 'Copy Path',
      icon: <Copy size={14} />,
      shortcut: isMac ? '⌥⌘C' : 'Shift+Alt+C',
      onClick: handleCopyPath,
    },
    {
      label: 'Copy Relative Path',
      icon: <Copy size={14} />,
      shortcut: isMac ? '⇧⌥⌘C' : 'Ctrl+Shift+Alt+C',
      onClick: handleCopyRelativePath,
    },
    ...(canCopyAsImport ? [{
      label: 'Copy as Import',
      icon: <FileCode size={14} />,
      onClick: handleCopyAsImport,
    }] : []),
    {
      label: 'Rename...',
      icon: <Pencil size={14} />,
      shortcut: isMac ? 'Enter' : 'F2',
      onClick: handleRename,
    },
    {
      label: 'Duplicate',
      icon: <Files size={14} />,
      shortcut: isMac ? '⌘D' : 'Ctrl+D',
      onClick: handleDuplicate,
    },
    {
      label: 'Delete',
      icon: <Trash2 size={14} />,
      shortcut: isMac ? '⌘⌫' : 'Delete',
      onClick: handleDelete,
      isDanger: true,
    },
  ];

  return (
    <div
      className="file-context-menu"
      ref={menuRef}
      style={{ left: position.x, top: position.y }}
      role="menu"
    >
      {menuItems.map((item, index) => (
        <button
          key={index}
          className={`context-menu-item ${item.isDanger ? 'danger' : ''}`}
          onClick={item.onClick}
          role="menuitem"
        >
          <span className="menu-item-icon">{item.icon}</span>
          <span className="menu-item-label">{item.label}</span>
          {item.shortcut && (
            <span className="menu-item-shortcut">{item.shortcut}</span>
          )}
        </button>
      ))}
    </div>
  );
}

export default FileContextMenu;
