/**
 * Review Pages Registry — central registry of all review page plugins.
 */

import type { ReviewPageProps, ReviewPageDefinition } from '../types';

import { Review3DView, Review3DViewDefinition } from './Review3DView';
import { Review2DRender, Review2DRenderDefinition } from './Review2DRender';
import { ReviewIBOM, ReviewIBOMDefinition } from './ReviewIBOM';
import { ReviewGerber, ReviewGerberDefinition } from './ReviewGerber';
import { ReviewDocuments, ReviewDocumentsDefinition } from './ReviewDocuments';

export interface ReviewPageEntry {
  definition: ReviewPageDefinition;
  component: React.ComponentType<ReviewPageProps>;
}

export const REVIEW_PAGES: ReviewPageEntry[] = [
  { definition: Review3DViewDefinition, component: Review3DView },
  { definition: Review2DRenderDefinition, component: Review2DRender },
  { definition: ReviewIBOMDefinition, component: ReviewIBOM },
  { definition: ReviewGerberDefinition, component: ReviewGerber },
  { definition: ReviewDocumentsDefinition, component: ReviewDocuments },
].sort((a, b) => a.definition.order - b.definition.order);
