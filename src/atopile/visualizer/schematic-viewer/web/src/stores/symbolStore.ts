import { create } from 'zustand';
import type { KicadSymbol, KicadSymbolLib, KicadPin } from '../types/symbol';
import { parseKicadSymbolLib } from '../lib/kicadSymParser';

interface SymbolState {
  // Data
  lib: KicadSymbolLib | null;
  activeIndex: number;
  isLoading: boolean;
  loadError: string | null;

  // Interaction
  hoveredPin: string | null;     // pin number
  selectedPin: KicadPin | null;
  highlightCategory: string | null;

  // Actions
  loadFromUrl: (url: string) => Promise<void>;
  loadFromString: (content: string, filename?: string) => void;
  setActiveIndex: (index: number) => void;
  setHoveredPin: (pinNumber: string | null) => void;
  setSelectedPin: (pin: KicadPin | null) => void;
  setHighlightCategory: (category: string | null) => void;
}

export const useSymbolStore = create<SymbolState>((set, get) => ({
  lib: null,
  activeIndex: 0,
  isLoading: false,
  loadError: null,
  hoveredPin: null,
  selectedPin: null,
  highlightCategory: null,

  loadFromUrl: async (url: string) => {
    set({ isLoading: true, loadError: null });
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      const text = await response.text();
      const lib = parseKicadSymbolLib(text);
      set({ lib, activeIndex: 0, isLoading: false, selectedPin: null, hoveredPin: null });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      set({ isLoading: false, loadError: msg });
    }
  },

  loadFromString: (content: string) => {
    try {
      const lib = parseKicadSymbolLib(content);
      set({ lib, activeIndex: 0, isLoading: false, loadError: null, selectedPin: null, hoveredPin: null });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Parse error';
      set({ loadError: msg });
    }
  },

  setActiveIndex: (index: number) => {
    set({ activeIndex: index, selectedPin: null, hoveredPin: null, highlightCategory: null });
  },

  setHoveredPin: (pinNumber) => set({ hoveredPin: pinNumber }),
  setSelectedPin: (pin) => set((s) => ({ selectedPin: s.selectedPin?.number === pin?.number ? null : pin })),
  setHighlightCategory: (category) => set((s) => ({
    highlightCategory: s.highlightCategory === category ? null : category,
  })),
}));

/** Convenience: get the currently active symbol. */
export function useActiveSymbol(): KicadSymbol | null {
  return useSymbolStore((s) => {
    if (!s.lib) return null;
    return s.lib.symbols[s.activeIndex] ?? null;
  });
}
