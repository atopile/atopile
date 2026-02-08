/**
 * ContextMenu — right-click alignment/distribution menu for multi-selected items.
 *
 * Rendered as an HTML overlay (not Three.js) for crisp text and native behavior.
 * Only appears when 2+ items are selected and user right-clicks.
 */

import { useCallback, useEffect, useRef } from 'react';
import type { ThemeColors } from '../lib/theme';
import { useSchematicStore, type AlignMode } from '../stores/schematicStore';

interface Props {
  theme: ThemeColors;
}

const MENU_ITEMS: { label: string; mode: AlignMode }[] = [
  { label: 'Align Left', mode: 'left' },
  { label: 'Align Right', mode: 'right' },
  { label: 'Align Top', mode: 'top' },
  { label: 'Align Bottom', mode: 'bottom' },
  { label: 'Center Horizontal', mode: 'center-h' },
  { label: 'Center Vertical', mode: 'center-v' },
  { label: 'Distribute Horizontal', mode: 'distribute-h' },
  { label: 'Distribute Vertical', mode: 'distribute-v' },
];

export function ContextMenu({ theme }: Props) {
  const contextMenu = useSchematicStore((s) => s.contextMenu);
  const closeContextMenu = useSchematicStore((s) => s.closeContextMenu);
  const alignSelected = useSchematicStore((s) => s.alignSelected);
  const selectedCount = useSchematicStore((s) => s.selectedComponentIds.length);
  const menuRef = useRef<HTMLDivElement>(null);

  const handleClick = useCallback(
    (mode: AlignMode) => {
      alignSelected(mode);
      closeContextMenu();
    },
    [alignSelected, closeContextMenu],
  );

  // Close on click outside
  useEffect(() => {
    if (!contextMenu) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        closeContextMenu();
      }
    };
    // Delay so the opening right-click doesn't immediately close
    const timer = setTimeout(() => {
      window.addEventListener('mousedown', handler);
    }, 0);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('mousedown', handler);
    };
  }, [contextMenu, closeContextMenu]);

  if (!contextMenu || selectedCount < 2) return null;

  return (
    <div
      ref={menuRef}
      style={{
        position: 'fixed',
        left: contextMenu.x,
        top: contextMenu.y,
        zIndex: 200,
        background: theme.bgSecondary,
        border: `1px solid ${theme.borderColor}`,
        borderRadius: 6,
        padding: '4px 0',
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        minWidth: 180,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: 12,
      }}
    >
      <div
        style={{
          padding: '4px 12px 6px',
          color: theme.textMuted,
          fontSize: 10,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        Align ({selectedCount} items)
      </div>
      {MENU_ITEMS.map((item) => (
        <button
          key={item.mode}
          onClick={() => handleClick(item.mode)}
          style={{
            display: 'block',
            width: '100%',
            padding: '6px 12px',
            background: 'none',
            border: 'none',
            color: theme.textPrimary,
            fontSize: 12,
            textAlign: 'left',
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
          onMouseEnter={(e) => {
            (e.target as HTMLButtonElement).style.background = theme.bgTertiary;
          }}
          onMouseLeave={(e) => {
            (e.target as HTMLButtonElement).style.background = 'none';
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
