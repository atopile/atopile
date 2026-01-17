/**
 * Filter state store using Zustand.
 */

import { create } from 'zustand';
import type { FilterConfig, EdgeTypeKey, GraphData } from '../types/graph';
import { getDefaultFilterConfig } from '../lib/filterEngine';

interface FilterState {
  config: FilterConfig;

  // Actions
  initializeFromData: (data: GraphData) => void;
  toggleNodeType: (typeName: string) => void;
  setNodeTypeExcluded: (typeName: string, excluded: boolean) => void;
  setAllNodeTypesExcluded: (excluded: boolean, allTypeNames?: string[]) => void;
  toggleTraitRequired: (traitName: string) => void;
  toggleTraitAny: (traitName: string) => void;
  toggleEdgeTypeVisible: (edgeType: EdgeTypeKey) => void;
  setAllEdgeTypesVisible: (visible: boolean) => void;
  setDepthRange: (min: number, max: number) => void;
  setHideAnonNodes: (hide: boolean) => void;
  setHideOrphans: (hide: boolean) => void;
  setReachability: (
    enabled: boolean,
    fromNodes?: Set<string>,
    edgeTypes?: Set<EdgeTypeKey>,
    maxHops?: number
  ) => void;
  resetFilters: () => void;
}

const ALL_EDGE_TYPES: EdgeTypeKey[] = [
  'composition',
  'trait',
  'pointer',
  'connection',
  'operand',
  'type',
  'next',
];

const INITIAL_CONFIG: FilterConfig = {
  nodeTypes: { included: new Set(), excluded: new Set() },
  traits: { required: new Set(), any: new Set() },
  edgeTypes: {
    visible: new Set(ALL_EDGE_TYPES),
  },
  depthRange: { min: 0, max: Infinity },
  hideAnonNodes: true, // Hide anonymous nodes by default
  hideOrphans: true, // Hide nodes whose parents are not visible
  reachability: null,
};

export const useFilterStore = create<FilterState>((set, get) => ({
  config: INITIAL_CONFIG,

  initializeFromData: (data: GraphData) => {
    const config = getDefaultFilterConfig(data);
    set({ config });
  },

  toggleNodeType: (typeName: string) => {
    const { config } = get();
    const newExcluded = new Set(config.nodeTypes.excluded);

    if (newExcluded.has(typeName)) {
      newExcluded.delete(typeName);
    } else {
      newExcluded.add(typeName);
    }

    set({
      config: {
        ...config,
        nodeTypes: {
          ...config.nodeTypes,
          excluded: newExcluded,
        },
      },
    });
  },

  setNodeTypeExcluded: (typeName: string, excluded: boolean) => {
    const { config } = get();
    const newExcluded = new Set(config.nodeTypes.excluded);

    if (excluded) {
      newExcluded.add(typeName);
    } else {
      newExcluded.delete(typeName);
    }

    set({
      config: {
        ...config,
        nodeTypes: {
          ...config.nodeTypes,
          excluded: newExcluded,
        },
      },
    });
  },

  setAllNodeTypesExcluded: (excluded: boolean, allTypeNames?: string[]) => {
    const { config } = get();
    set({
      config: {
        ...config,
        nodeTypes: {
          included: config.nodeTypes.included,
          excluded: excluded && allTypeNames ? new Set(allTypeNames) : new Set(),
        },
      },
    });
  },

  setAllEdgeTypesVisible: (visible: boolean) => {
    const { config } = get();
    set({
      config: {
        ...config,
        edgeTypes: {
          visible: visible ? new Set(ALL_EDGE_TYPES) : new Set(),
        },
      },
    });
  },

  setHideAnonNodes: (hide: boolean) => {
    const { config } = get();
    set({
      config: {
        ...config,
        hideAnonNodes: hide,
      },
    });
  },

  setHideOrphans: (hide: boolean) => {
    const { config } = get();
    set({
      config: {
        ...config,
        hideOrphans: hide,
      },
    });
  },

  toggleTraitRequired: (traitName: string) => {
    const { config } = get();
    const newRequired = new Set(config.traits.required);

    if (newRequired.has(traitName)) {
      newRequired.delete(traitName);
    } else {
      newRequired.add(traitName);
    }

    set({
      config: {
        ...config,
        traits: {
          ...config.traits,
          required: newRequired,
        },
      },
    });
  },

  toggleTraitAny: (traitName: string) => {
    const { config } = get();
    const newAny = new Set(config.traits.any);

    if (newAny.has(traitName)) {
      newAny.delete(traitName);
    } else {
      newAny.add(traitName);
    }

    set({
      config: {
        ...config,
        traits: {
          ...config.traits,
          any: newAny,
        },
      },
    });
  },

  toggleEdgeTypeVisible: (edgeType: EdgeTypeKey) => {
    const { config } = get();
    const newVisible = new Set(config.edgeTypes.visible);

    if (newVisible.has(edgeType)) {
      newVisible.delete(edgeType);
    } else {
      newVisible.add(edgeType);
    }

    set({
      config: {
        ...config,
        edgeTypes: {
          visible: newVisible,
        },
      },
    });
  },

  setDepthRange: (min: number, max: number) => {
    const { config } = get();
    set({
      config: {
        ...config,
        depthRange: { min, max },
      },
    });
  },

  setReachability: (
    enabled: boolean,
    fromNodes?: Set<string>,
    edgeTypes?: Set<EdgeTypeKey>,
    maxHops?: number
  ) => {
    const { config } = get();

    if (!enabled) {
      set({
        config: {
          ...config,
          reachability: null,
        },
      });
      return;
    }

    set({
      config: {
        ...config,
        reachability: {
          enabled: true,
          fromNodes: fromNodes ?? config.reachability?.fromNodes ?? new Set(),
          edgeTypes:
            edgeTypes ??
            config.reachability?.edgeTypes ??
            new Set(['composition', 'connection'] as EdgeTypeKey[]),
          maxHops: maxHops ?? config.reachability?.maxHops ?? 3,
        },
      },
    });
  },

  resetFilters: () => {
    set({ config: INITIAL_CONFIG });
  },
}));
