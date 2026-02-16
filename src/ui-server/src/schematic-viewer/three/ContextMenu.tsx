/**
 * ContextMenu — right-click context actions for alignment, ports, and source links.
 *
 * Rendered as an HTML overlay (not Three.js) for crisp text and native behavior.
 */

import { useCallback, useEffect, useMemo, useRef } from 'react';
import type { ThemeColors } from '../utils/theme';
import { useCurrentPorts, useCurrentSheet, useSchematicStore, type AlignMode } from '../stores/schematicStore';
import { postToExtension } from '../utils/vscodeApi';

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
  const setPortEditMode = useSchematicStore((s) => s.setPortEditMode);
  const portEditMode = useSchematicStore((s) => s.portEditMode);
  const portEditTargetId = useSchematicStore((s) => s.portEditTargetId);
  const selectedComponentId = useSchematicStore((s) => s.selectedComponentId);
  const selectedCount = useSchematicStore((s) => s.selectedComponentIds.length);
  const sheet = useCurrentSheet();
  const ports = useCurrentPorts();
  const menuRef = useRef<HTMLDivElement>(null);

  const handleClick = useCallback(
    (mode: AlignMode) => {
      alignSelected(mode);
      closeContextMenu();
    },
    [alignSelected, closeContextMenu],
  );

  const handlePortEditToggle = useCallback(() => {
    const targetId = contextMenu?.targetId ?? null;
    if (!targetId && !portEditMode) {
      closeContextMenu();
      return;
    }
    if (portEditMode && (!targetId || targetId === portEditTargetId)) {
      setPortEditMode(false);
    } else {
      setPortEditMode(true, targetId);
    }
    closeContextMenu();
  }, [setPortEditMode, portEditMode, portEditTargetId, contextMenu, closeContextMenu]);

  const menuTargetId = contextMenu?.targetId ?? selectedComponentId ?? null;
  const source = useMemo(() => {
    if (!menuTargetId) return null;
    return sheet?.components.find((c) => c.id === menuTargetId)?.source
      ?? sheet?.modules.find((m) => m.id === menuTargetId)?.source
      ?? ports.find((p) => p.id === menuTargetId)?.source
      ?? null;
  }, [menuTargetId, sheet, ports]);
  const fallbackAddress = menuTargetId && menuTargetId.includes('::')
    ? menuTargetId
    : undefined;
  const openSourceRequest = useMemo(() => {
    const address = source?.address ?? fallbackAddress;
    const filePath = source?.filePath;
    if (!address && !filePath) return null;
    return {
      address,
      filePath,
      line: source?.line,
      column: source?.column,
    };
  }, [source, fallbackAddress]);
  const revealSourceRequest = useMemo(() => {
    const address = source?.address ?? fallbackAddress;
    const filePath = source?.filePath;
    if (!address && !filePath) return null;
    return { address, filePath };
  }, [source, fallbackAddress]);
  const handleOpenSource = useCallback(() => {
    if (!openSourceRequest) return;
    postToExtension({
      type: 'openSource',
      ...openSourceRequest,
    });
    closeContextMenu();
  }, [openSourceRequest, closeContextMenu]);
  const handleRevealSource = useCallback(() => {
    if (!revealSourceRequest) return;
    postToExtension({
      type: 'revealInExplorer',
      ...revealSourceRequest,
    });
    closeContextMenu();
  }, [revealSourceRequest, closeContextMenu]);

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

  if (!contextMenu) return null;
  if (contextMenu.kind === 'align' && selectedCount < 2) return null;
  if (contextMenu.kind === 'port' && !contextMenu.targetId && !portEditMode) return null;
  if (contextMenu.kind === 'selection' && !menuTargetId) return null;

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
      {contextMenu.kind === 'align' ? (
        <>
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
            <MenuButton
              key={item.mode}
              theme={theme}
              label={item.label}
              onClick={() => handleClick(item.mode)}
            />
          ))}
        </>
      ) : contextMenu.kind === 'port' ? (
        <>
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
            Ports
          </div>
          <MenuButton
            theme={theme}
            onClick={handlePortEditToggle}
            label={
              portEditMode && (!contextMenu.targetId || contextMenu.targetId === portEditTargetId)
                ? 'Done Editing Ports'
                : portEditMode
                  ? 'Edit These Ports'
                  : 'Edit Ports'
            }
          />
          {(openSourceRequest || revealSourceRequest) && (
            <>
              <div
                style={{
                  margin: '4px 0',
                  borderTop: `1px solid ${theme.borderColor}`,
                }}
              />
              <MenuButton
                theme={theme}
                label="Open in ato"
                disabled={!openSourceRequest}
                onClick={handleOpenSource}
              />
              <MenuButton
                theme={theme}
                label="Reveal in Explorer"
                disabled={!revealSourceRequest}
                onClick={handleRevealSource}
              />
            </>
          )}
        </>
      ) : (
        <>
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
            Symbol
          </div>
          <MenuButton
            theme={theme}
            label="Open in ato"
            disabled={!openSourceRequest}
            onClick={handleOpenSource}
          />
          <MenuButton
            theme={theme}
            label="Reveal in Explorer"
            disabled={!revealSourceRequest}
            onClick={handleRevealSource}
          />
        </>
      )}
    </div>
  );
}

function MenuButton({
  theme,
  label,
  onClick,
  disabled,
}: {
  theme: ThemeColors;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'block',
        width: '100%',
        padding: '6px 12px',
        background: 'none',
        border: 'none',
        color: disabled ? theme.textMuted : theme.textPrimary,
        fontSize: 12,
        textAlign: 'left',
        cursor: disabled ? 'default' : 'pointer',
        fontFamily: 'inherit',
      }}
      onMouseEnter={(e) => {
        if (disabled) return;
        (e.target as HTMLButtonElement).style.background = theme.bgTertiary;
      }}
      onMouseLeave={(e) => {
        if (disabled) return;
        (e.target as HTMLButtonElement).style.background = 'none';
      }}
    >
      {label}
    </button>
  );
}
