/**
 * Toolbar — top bar for the schematic viewer.
 * Shows breadcrumb navigation and key controls.
 */

import { useMemo, type CSSProperties } from 'react';
import { useEffect, useState } from 'react';
import {
  useSchematicStore,
  useCurrentSheet,
} from '../stores/schematicStore';
import { getRootSheet, getPathLabels } from '../types/schematic';
import { useTheme } from '../lib/theme';
import type { ThemeColors } from '../lib/theme';
import './Toolbar.css';

export type SchematicBuildPhase = 'idle' | 'building' | 'queued' | 'success' | 'failed';

export interface SchematicBuildStatus {
  phase: SchematicBuildPhase;
  dirty: boolean;
  viewingLastSuccessful: boolean;
  lastSuccessfulAt: number | null;
  message: string | null;
}

function buildStatusStyle(
  status: SchematicBuildStatus,
  theme: ThemeColors,
): { text: string; bg: string; fg: string; border: string } {
  switch (status.phase) {
    case 'building':
      return {
        text: 'Building...',
        bg: `${theme.accent}22`,
        fg: theme.textPrimary,
        border: `${theme.accent}66`,
      };
    case 'queued':
      return {
        text: 'Queued',
        bg: `${theme.bgTertiary}`,
        fg: theme.textSecondary,
        border: theme.borderColor,
      };
    case 'success':
      return {
        text: 'Built',
        bg: '#3c6f3b33',
        fg: '#9fe29b',
        border: '#4f8e4d99',
      };
    case 'failed':
      return {
        text: 'Failed',
        bg: '#7d2b3e33',
        fg: '#f5a7ba',
        border: '#a8455f99',
      };
    case 'idle':
    default:
      return {
        text: status.dirty ? 'Dirty' : 'Idle',
        bg: theme.bgTertiary,
        fg: theme.textMuted,
        border: theme.borderColor,
      };
  }
}

function buildViewingText(status: SchematicBuildStatus): string {
  if (status.viewingLastSuccessful && (status.dirty || status.phase === 'failed')) return 'View: last successful';
  if (status.viewingLastSuccessful) return 'View: last successful';
  if (status.dirty || status.phase === 'failed') return 'View: dirty/failed';
  return 'View: latest';
}

function formatRelativeAge(epochMs: number, nowMs: number): string {
  const diffMs = Math.max(0, nowMs - epochMs);
  const secs = Math.floor(diffMs / 1000);
  const mins = Math.floor(secs / 60);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);

  if (secs < 10) return 'just now';
  if (secs < 60) return `${secs}s ago`;
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days}d ago`;
  return new Date(epochMs).toLocaleDateString();
}

function buildFreshnessText(
  status: SchematicBuildStatus,
  nowMs: number,
): { text: string; tone: 'live' | 'stale' | 'muted' } {
  if (status.phase === 'building') return { text: 'Live · rebuilding', tone: 'live' };
  if (status.phase === 'queued') return { text: 'Live · queued', tone: 'live' };

  if (!status.lastSuccessfulAt) {
    if (status.phase === 'failed' || status.dirty) {
      return { text: 'No successful build yet', tone: 'stale' };
    }
    return { text: 'Waiting for first build', tone: 'muted' };
  }

  const age = formatRelativeAge(status.lastSuccessfulAt, nowMs);
  if (status.phase === 'failed') return { text: `Generated ${age} · failed`, tone: 'stale' };
  if (status.dirty) return { text: `Generated ${age} · dirty`, tone: 'stale' };
  if (status.viewingLastSuccessful) return { text: `Generated ${age} · snapshot`, tone: 'muted' };
  return { text: `Generated ${age} · live`, tone: 'live' };
}

export function Toolbar({
  buildStatus,
  sidebarCollapsed,
  onToggleSidebar,
}: {
  buildStatus: SchematicBuildStatus;
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
}) {
  const schematic = useSchematicStore((s) => s.schematic);
  const currentPath = useSchematicStore((s) => s.currentPath);
  const navigateToPath = useSchematicStore((s) => s.navigateToPath);
  const navigateUp = useSchematicStore((s) => s.navigateUp);
  const resetLayout = useSchematicStore((s) => s.resetLayout);
  const currentSheet = useCurrentSheet();
  const theme = useTheme();
  const statusPill = buildStatusStyle(buildStatus, theme);
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    const intervalId = window.setInterval(() => setNowMs(Date.now()), 15_000);
    return () => window.clearInterval(intervalId);
  }, []);

  const pathLabels = useMemo(() => {
    if (!schematic) return [];
    return getPathLabels(getRootSheet(schematic), currentPath);
  }, [schematic, currentPath]);

  const cssVars = {
    '--st-bg': theme.bgSecondary,
    '--st-border': theme.borderColor,
    '--st-hover': theme.bgHover,
    '--st-elev': theme.bgTertiary,
    '--st-text': theme.textPrimary,
    '--st-secondary': theme.textSecondary,
    '--st-muted': theme.textMuted,
    '--st-accent': theme.accent,
    '--st-status-bg': statusPill.bg,
    '--st-status-fg': statusPill.fg,
    '--st-status-border': statusPill.border,
  } as CSSProperties;
  const freshness = buildFreshnessText(buildStatus, nowMs);
  const freshnessTitle = buildStatus.lastSuccessfulAt
    ? `Last successful build: ${new Date(buildStatus.lastSuccessfulAt).toLocaleString()}`
    : 'No successful schematic build yet';

  return (
    <div className="schematic-toolbar" style={cssVars}>
      <div className="schematic-toolbar-brand">SCH</div>
      <div className="schematic-toolbar-divider" />

      <div className="schematic-toolbar-breadcrumbs">
        <BreadcrumbItem
          label="Root"
          isActive={currentPath.length === 0}
          onClick={() => navigateToPath([])}
          theme={theme}
        />

        {pathLabels.map((seg, i) => (
          <div key={seg.id} className="schematic-toolbar-breadcrumb-item">
            <span className="schematic-toolbar-separator">/</span>
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
            className="schematic-toolbar-button subtle"
            title="Go up one level (Backspace)"
          >
            Up
          </button>
        )}
      </div>

      <div className="schematic-toolbar-spacer" />

      <span
        className={`schematic-toolbar-freshness ${freshness.tone}`}
        title={freshnessTitle}
      >
        {freshness.text}
      </span>

      <span className="schematic-toolbar-view-text">{buildViewingText(buildStatus)}</span>

      <div className="schematic-toolbar-status">
        {statusPill.text}
      </div>

      {currentSheet && (
        <button
          onClick={resetLayout}
          className="schematic-toolbar-button"
          title="Reset symbol layout positions"
        >
          Reset layout
        </button>
      )}

      <button
        onClick={onToggleSidebar}
        className={`schematic-toolbar-button ${sidebarCollapsed ? 'active' : ''}`}
        title={sidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}
      >
        {sidebarCollapsed ? 'Show inspector' : 'Hide inspector'}
      </button>
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
      className={`schematic-toolbar-crumb ${isActive ? 'active' : ''}`}
      title={subtitle ? `${label} (${subtitle})` : label}
      style={{
        maxWidth: 160,
        color: isActive ? theme.textPrimary : theme.textSecondary,
      }}
    >
      {label}
    </button>
  );
}
