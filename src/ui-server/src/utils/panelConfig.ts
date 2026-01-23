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
  buildQueue: {
    id: 'buildQueue',
    minHeight: 60,
    preferredHeight: 120,
    maxHeight: 240,
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
  problems: {
    id: 'problems',
    minHeight: 80,
    preferredHeight: 180,
    maxHeight: 350,
    priority: 'high',
    collapseWhenEmpty: true,
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
  'buildQueue',
  'packages',
  'problems',
  'stdlib',
  'variables',
  'bom',
] as const;

export type PanelId = typeof PANEL_IDS[number];

// Title bar height when collapsed (px)
export const COLLAPSED_HEIGHT = 32;
