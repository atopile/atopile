/**
 * View Pages Registry — central registry of all view page plugins.
 */

import type { ViewPageProps, ViewPageDefinition } from '../types';

import { VisualView, VisualViewDefinition } from './VisualView';
import { ReviewGerber, ReviewGerberDefinition } from './ReviewGerber';
import { ReviewIBOM, ReviewIBOMDefinition } from './ReviewIBOM';

export interface ViewPageEntry {
  definition: ViewPageDefinition;
  component: React.ComponentType<ViewPageProps>;
}

export const VIEW_PAGES: ViewPageEntry[] = [
  { definition: VisualViewDefinition, component: VisualView },
  { definition: ReviewGerberDefinition, component: ReviewGerber },
  { definition: ReviewIBOMDefinition, component: ReviewIBOM },
].sort((a, b) => a.definition.order - b.definition.order);
