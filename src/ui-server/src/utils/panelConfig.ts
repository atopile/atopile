/**
 * Unified Panel Configuration
 * All panel sizing and behavior configuration in one place.
 */

export interface PanelConfig {
  id: string;
  minHeight: number;        // Minimum when expanded
  preferredHeight: number;  // Ideal height based on content type
  maxHeight: number;        // Cap before scrolling
  priority: 'high' | 'normal' | 'low';
  collapseWhenEmpty: boolean;
}

export const PANEL_CONFIGS: Record<string, PanelConfig> = {
  projects: {
    id: 'projects',
    minHeight: 80,
    preferredHeight: 200,
    maxHeight: 400,
    priority: 'high',
    collapseWhenEmpty: false,
  },
  structure: {
    id: 'structure',
    minHeight: 80,
    preferredHeight: 180,
    maxHeight: 360,
    priority: 'normal',
    collapseWhenEmpty: true,
  },
  packages: {
    id: 'packages',
    minHeight: 80,
    preferredHeight: 200,
    maxHeight: 400,
    priority: 'normal',
    collapseWhenEmpty: false,
  },
  stdlib: {
    id: 'stdlib',
    minHeight: 80,
    preferredHeight: 180,
    maxHeight: 300,
    priority: 'low',
    collapseWhenEmpty: false,
  },
  variables: {
    id: 'variables',
    minHeight: 80,
    preferredHeight: 150,
    maxHeight: 300,
    priority: 'normal',
    collapseWhenEmpty: true,
  },
  bom: {
    id: 'bom',
    minHeight: 100,
    preferredHeight: 200,
    maxHeight: 400,
    priority: 'low',
    collapseWhenEmpty: false,
  },
};

// All panel IDs in display order
export const PANEL_IDS = [
  'projects',
  'structure',
  'packages',
  'stdlib',
  'variables',
  'bom',
] as const;

export type PanelId = typeof PANEL_IDS[number];

// Title bar height when collapsed (px)
export const COLLAPSED_HEIGHT = 32;
