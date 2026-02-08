/**
 * Toolbar — top bar for the schematic viewer.
 * Shows breadcrumb navigation, sheet stats, and controls.
 */

import { useMemo } from 'react';
import {
  useSchematicStore,
  useCurrentSheet,
} from '../stores/schematicStore';
import { getRootSheet, getPathLabels } from '../types/schematic';
import { useTheme } from '../lib/theme';
import type { ThemeColors } from '../lib/theme';

export function Toolbar() {
  const schematic = useSchematicStore((s) => s.schematic);
  const currentPath = useSchematicStore((s) => s.currentPath);
  const navigateToPath = useSchematicStore((s) => s.navigateToPath);
  const navigateUp = useSchematicStore((s) => s.navigateUp);
  const resetLayout = useSchematicStore((s) => s.resetLayout);
  const sheet = useCurrentSheet();
  const theme = useTheme();

  const pathLabels = useMemo(() => {
    if (!schematic) return [];
    return getPathLabels(getRootSheet(schematic), currentPath);
  }, [schematic, currentPath]);

  const netCount = sheet?.nets.length ?? 0;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '0 16px',
        height: 40,
        flexShrink: 0,
        background: theme.bgSecondary,
        borderBottom: `1px solid ${theme.borderColor}`,
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.05em',
            color: theme.accent,
          }}
        >
          SCH
        </span>
      </div>

      <div
        style={{ width: 1, height: 16, background: theme.borderColor }}
      />

      {/* Breadcrumbs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 0 }}>
        <BreadcrumbItem
          label="Root"
          isActive={currentPath.length === 0}
          onClick={() => navigateToPath([])}
          theme={theme}
        />

        {pathLabels.map((seg, i) => (
          <div key={seg.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ fontSize: 11, color: theme.textMuted }}>/</span>
            <BreadcrumbItem
              label={seg.name}
              subtitle={seg.typeName}
              isActive={i === pathLabels.length - 1}
              onClick={() => navigateToPath(currentPath.slice(0, i + 1))}
              theme={theme}
            />
          </div>
        ))}

        {currentPath.length > 0 && (
          <button
            onClick={navigateUp}
            style={{
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 3,
              marginLeft: 8,
              background: theme.bgTertiary,
              color: theme.textSecondary,
              border: `1px solid ${theme.borderColor}`,
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = theme.bgHover;
              e.currentTarget.style.color = theme.textPrimary;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = theme.bgTertiary;
              e.currentTarget.style.color = theme.textSecondary;
            }}
            title="Go up one level (Backspace)"
          >
            {'<-'} Up
          </button>
        )}
      </div>

      <div
        style={{ width: 1, height: 16, background: theme.borderColor }}
      />

      {/* Stats */}
      {sheet && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {sheet.modules.length > 0 && (
            <span style={{ fontSize: 11, color: theme.textSecondary }}>
              {sheet.modules.length} modules
            </span>
          )}
          {sheet.components.length > 0 && (
            <span style={{ fontSize: 11, color: theme.textSecondary }}>
              {sheet.components.length} components
            </span>
          )}
          <span style={{ fontSize: 11, color: theme.textMuted }}>&middot;</span>
          <span style={{ fontSize: 11, color: theme.textSecondary }}>
            {netCount} nets
          </span>
        </div>
      )}

      <div style={{ flex: 1 }} />

      {/* Hints */}
      <span style={{ fontSize: 11, color: theme.textMuted }}>
        {currentPath.length > 0
          ? 'backspace to go up'
          : 'double-click module to enter'}
        {' \u00B7 '}drag to move{' \u00B7 '}right-drag to pan
      </span>

      {/* Reset layout */}
      {sheet && (
        <button
          onClick={resetLayout}
          style={{
            fontSize: 11,
            padding: '4px 12px',
            borderRadius: 3,
            background: theme.bgTertiary,
            color: theme.textSecondary,
            border: `1px solid ${theme.borderColor}`,
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = theme.bgHover;
            e.currentTarget.style.color = theme.textPrimary;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = theme.bgTertiary;
            e.currentTarget.style.color = theme.textSecondary;
          }}
        >
          Reset Layout
        </button>
      )}
    </div>
  );
}

function BreadcrumbItem({
  label,
  subtitle,
  isActive,
  onClick,
  theme,
}: {
  label: string;
  subtitle?: string;
  isActive: boolean;
  onClick: () => void;
  theme: ThemeColors;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        fontSize: 11,
        padding: '2px 6px',
        borderRadius: 3,
        maxWidth: 120,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        color: isActive ? theme.textPrimary : theme.textSecondary,
        background: isActive ? theme.bgTertiary : 'transparent',
        fontWeight: isActive ? 600 : 400,
        border: 'none',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => {
        if (!isActive) {
          e.currentTarget.style.background = theme.bgHover;
          e.currentTarget.style.color = theme.textPrimary;
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive) {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = theme.textSecondary;
        }
      }}
      title={subtitle ? `${label} (${subtitle})` : label}
    >
      {label}
    </button>
  );
}
