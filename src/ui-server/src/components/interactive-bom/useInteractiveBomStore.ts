import { create } from 'zustand';
import type { RenderModel } from '@layout-viewer/types';
import type { BomGroup, BomEnrichment } from './types';
import { buildBomGroups } from './bomGrouping';

interface InteractiveBomState {
  renderModel: RenderModel | null;
  bomGroups: BomGroup[];
  fpIndexToGroupId: Map<number, string>;
  selectedGroupId: string | null;
  hoveredGroupId: string | null;
  searchQuery: string;
  isRegex: boolean;
  caseSensitive: boolean;
  bomEnrichment: Map<string, BomEnrichment>;

  setRenderModel: (model: RenderModel) => void;
  setSelectedGroup: (groupId: string | null) => void;
  setHoveredGroup: (groupId: string | null) => void;
  setSearchQuery: (query: string) => void;
  setIsRegex: (isRegex: boolean) => void;
  setCaseSensitive: (caseSensitive: boolean) => void;
  setBomEnrichment: (enrichment: Map<string, BomEnrichment>) => void;
}

export const useInteractiveBomStore = create<InteractiveBomState>((set) => ({
  renderModel: null,
  bomGroups: [],
  fpIndexToGroupId: new Map(),
  selectedGroupId: null,
  hoveredGroupId: null,
  searchQuery: '',
  isRegex: false,
  caseSensitive: false,
  bomEnrichment: new Map(),

  setRenderModel: (model) => {
    const { bomGroups, fpIndexToGroupId } = buildBomGroups(model);
    set({ renderModel: model, bomGroups, fpIndexToGroupId });
  },

  setSelectedGroup: (groupId) => set({ selectedGroupId: groupId }),
  setHoveredGroup: (groupId) => set({ hoveredGroupId: groupId }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setIsRegex: (isRegex) => set({ isRegex }),
  setCaseSensitive: (caseSensitive) => set({ caseSensitive }),
  setBomEnrichment: (enrichment) => set({ bomEnrichment: enrichment }),
}));
