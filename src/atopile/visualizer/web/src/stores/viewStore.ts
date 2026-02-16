/**
 * View state store using Zustand.
 *
 * Manages camera position, zoom, and view settings with animation support.
 */

import { create } from 'zustand';

interface CameraTarget {
  position: { x: number; y: number; z: number };
  lookAt: { x: number; y: number; z: number };
}

export type ColorScheme = 'type' | 'depth' | 'trait' | 'parent';

interface ViewState {
  zoom: number;
  center: { x: number; y: number; z: number };
  cameraPosition: { x: number; y: number; z: number };
  is3D: boolean;
  showLabels: boolean;
  labelMinZoom: number;
  colorScheme: ColorScheme;

  // Animation state
  animationTarget: CameraTarget | null;
  isAnimating: boolean;

  // Actions
  setZoom: (zoom: number) => void;
  setCenter: (center: { x: number; y: number; z: number }) => void;
  setCameraPosition: (pos: { x: number; y: number; z: number }) => void;
  toggle3D: () => void;
  toggleLabels: () => void;
  setLabelMinZoom: (zoom: number) => void;
  setColorScheme: (scheme: ColorScheme) => void;
  resetView: () => void;
  fitToView: (bounds: { minX: number; maxX: number; minY: number; maxY: number }) => void;

  // Animation actions
  animateTo: (target: CameraTarget) => void;
  clearAnimation: () => void;
}

export const useViewStore = create<ViewState>((set) => ({
  zoom: 1,
  center: { x: 0, y: 0, z: 0 },
  cameraPosition: { x: 0, y: 0, z: 500 },
  is3D: false,
  showLabels: true,
  labelMinZoom: 0.5,
  colorScheme: 'type',
  animationTarget: null,
  isAnimating: false,

  setZoom: (zoom: number) => {
    set({ zoom: Math.max(0.1, Math.min(10, zoom)) });
  },

  setCenter: (center: { x: number; y: number; z: number }) => {
    set({ center });
  },

  setCameraPosition: (pos: { x: number; y: number; z: number }) => {
    set({ cameraPosition: pos });
  },

  toggle3D: () => {
    set((state) => ({ is3D: !state.is3D }));
  },

  toggleLabels: () => {
    set((state) => ({ showLabels: !state.showLabels }));
  },

  setLabelMinZoom: (zoom: number) => {
    set({ labelMinZoom: zoom });
  },

  setColorScheme: (scheme: ColorScheme) => {
    set({ colorScheme: scheme });
  },

  resetView: () => {
    set({
      animationTarget: {
        position: { x: 0, y: 0, z: 500 },
        lookAt: { x: 0, y: 0, z: 0 },
      },
      isAnimating: true,
      zoom: 1,
      center: { x: 0, y: 0, z: 0 },
    });
  },

  fitToView: (bounds) => {
    const width = bounds.maxX - bounds.minX;
    const height = bounds.maxY - bounds.minY;
    const maxDim = Math.max(width, height, 1);

    // Calculate zoom to fit bounds in view
    const zoom = 400 / maxDim;
    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;
    const cameraZ = Math.max(maxDim * 1.5, 200);

    set({
      animationTarget: {
        position: { x: centerX, y: centerY, z: cameraZ },
        lookAt: { x: centerX, y: centerY, z: 0 },
      },
      isAnimating: true,
      zoom: Math.max(0.1, Math.min(10, zoom)),
      center: { x: centerX, y: centerY, z: 0 },
    });
  },

  animateTo: (target) => {
    set({
      animationTarget: target,
      isAnimating: true,
    });
  },

  clearAnimation: () => {
    set({
      animationTarget: null,
      isAnimating: false,
    });
  },
}));
