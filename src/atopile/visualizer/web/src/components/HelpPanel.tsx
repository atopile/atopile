/**
 * Help panel showing keyboard shortcuts and usage tips.
 */

import { useState } from 'react';

interface HelpPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const SHORTCUTS = [
  { key: 'Ctrl+K', description: 'Focus search bar' },
  { key: 'F', description: 'Fit graph to view' },
  { key: 'Esc', description: 'Clear selection' },
  { key: 'L', description: 'Toggle labels' },
  { key: 'R', description: 'Re-run layout' },
  { key: 'E', description: 'Expand all nodes' },
  { key: 'C', description: 'Toggle collapse on selected' },
  { key: 'H', description: 'Reset view (home)' },
];

const MOUSE_CONTROLS = [
  { action: 'Left-click', description: 'Select node' },
  { action: 'Shift + click', description: 'Add to selection' },
  { action: 'Double-click', description: 'Focus on node' },
  { action: 'Click empty', description: 'Clear selection' },
  { action: 'Drag', description: 'Rotate view' },
  { action: 'Right-drag', description: 'Pan view' },
  { action: 'Scroll', description: 'Zoom in/out' },
];

export function HelpPanel({ isOpen, onClose }: HelpPanelProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-[11000]"
      onClick={onClose}
    >
      <div
        className="bg-panel-bg border border-panel-border rounded-lg shadow-2xl max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-panel-border">
          <h2 className="text-lg font-semibold text-text-primary">
            Graph Visualizer Help
          </h2>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M4 4l12 12M16 4L4 16" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-6">
          {/* Keyboard shortcuts */}
          <section>
            <h3 className="text-sm font-medium text-text-primary mb-3">
              Keyboard Shortcuts
            </h3>
            <div className="space-y-2">
              {SHORTCUTS.map(({ key, description }) => (
                <div key={key} className="flex items-center gap-3">
                  <kbd className="px-2 py-1 text-xs font-mono bg-graph-bg rounded border border-panel-border text-text-primary min-w-[3rem] text-center">
                    {key}
                  </kbd>
                  <span className="text-sm text-text-secondary">{description}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Mouse controls */}
          <section>
            <h3 className="text-sm font-medium text-text-primary mb-3">
              Mouse Controls
            </h3>
            <div className="space-y-2">
              {MOUSE_CONTROLS.map(({ action, description }) => (
                <div key={action} className="flex items-center gap-3">
                  <span className="text-xs font-medium text-accent min-w-[6rem]">
                    {action}
                  </span>
                  <span className="text-sm text-text-secondary">{description}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Tips */}
          <section>
            <h3 className="text-sm font-medium text-text-primary mb-3">Tips</h3>
            <ul className="space-y-2 text-sm text-text-secondary list-disc list-inside">
              <li>Use the sidebar to filter nodes by type or edge type</li>
              <li>Collapse nodes to simplify complex graphs</li>
              <li>Use reachability to explore connections from selected nodes</li>
              <li>The inspector shows details when you select a node</li>
              <li>Labels appear automatically based on zoom level</li>
            </ul>
          </section>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-panel-border">
          <button
            onClick={onClose}
            className="w-full py-2 px-4 bg-accent text-white rounded hover:bg-accent/90 transition-colors text-sm font-medium"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Help button component.
 */
export function HelpButton() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="p-2 text-text-secondary hover:text-text-primary hover:bg-panel-border rounded transition-colors"
        title="Help (?)"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </button>

      <HelpPanel isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  );
}
