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

  const compCount = sheet
    ? sheet.components.length + sheet.modules.length
    : 0;
  const netCount = sheet?.nets.length ?? 0;

  return (
    <div
      className="flex items-center gap-3 px-4 h-10 flex-shrink-0"
      style={{
        background: theme.bgSecondary,
        borderBottom: `1px solid ${theme.borderColor}`,
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2">
        <span
          className="text-xs font-bold tracking-wider"
          style={{ color: theme.accent }}
        >
          SCH
        </span>
      </div>

      <div
        style={{ width: 1, height: 16, background: theme.borderColor }}
      />

      {/* ── Breadcrumbs ──────────────────────────────── */}
      <div className="flex items-center gap-1 min-w-0">
        {/* Root */}
        <BreadcrumbItem
          label="Root"
          isActive={currentPath.length === 0}
          onClick={() => navigateToPath([])}
          theme={theme}
        />

        {/* Path segments */}
        {pathLabels.map((seg, i) => (
          <div key={seg.id} className="flex items-center gap-1">
            <span
              className="text-xs"
              style={{ color: theme.textMuted }}
            >
              /
            </span>
            <BreadcrumbItem
              label={seg.name}
              subtitle={seg.typeName}
              isActive={i === pathLabels.length - 1}
              onClick={() =>
                navigateToPath(currentPath.slice(0, i + 1))
              }
              theme={theme}
            />
          </div>
        ))}

        {/* Back button when inside a module */}
        {currentPath.length > 0 && (
          <button
            onClick={navigateUp}
            className="text-xs px-2 py-0.5 rounded ml-2 transition-colors"
            style={{
              background: theme.bgTertiary,
              color: theme.textSecondary,
              border: `1px solid ${theme.borderColor}`,
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
        <div className="flex items-center gap-3">
          {sheet.modules.length > 0 && (
            <span
              className="text-xs"
              style={{ color: theme.textSecondary }}
            >
              {sheet.modules.length} modules
            </span>
          )}
          {sheet.components.length > 0 && (
            <span
              className="text-xs"
              style={{ color: theme.textSecondary }}
            >
              {sheet.components.length} components
            </span>
          )}
          <span
            className="text-xs"
            style={{ color: theme.textMuted }}
          >
            &middot;
          </span>
          <span
            className="text-xs"
            style={{ color: theme.textSecondary }}
          >
            {netCount} nets
          </span>
        </div>
      )}

      <div className="flex-1" />

      {/* Hints */}
      <span
        className="text-xs hidden sm:inline"
        style={{ color: theme.textMuted }}
      >
        {currentPath.length > 0
          ? 'backspace to go up'
          : 'double-click module to enter'}
        {' \u00B7 '}drag to move{' \u00B7 '}right-drag to pan
      </span>

      {/* Reset layout */}
      {sheet && (
        <button
          onClick={resetLayout}
          className="text-xs px-3 py-1 rounded transition-colors"
          style={{
            background: theme.bgTertiary,
            color: theme.textSecondary,
            border: `1px solid ${theme.borderColor}`,
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

// ── Breadcrumb item ────────────────────────────────────────────

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
      className="text-xs px-1.5 py-0.5 rounded transition-colors truncate max-w-[120px]"
      style={{
        color: isActive ? theme.textPrimary : theme.textSecondary,
        background: isActive ? theme.bgTertiary : 'transparent',
        fontWeight: isActive ? 600 : 400,
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
