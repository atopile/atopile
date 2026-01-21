/**
 * Action button component with modern styling.
 */

import './ActionButton.css';

interface ActionButtonProps {
  icon: string;
  label: string;
  tooltip: string;
  onClick: () => void;
}

// Map VS Code codicon names to SVG icons
function getIcon(iconName: string) {
  const icons: Record<string, JSX.Element> = {
    play: (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M4 2l10 6-10 6V2z" />
      </svg>
    ),
    'file-binary': (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M10 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V4l-3-3zm2 13H4V2h5v3h3v9z" />
        <path d="M6 7h1v4H6V7zm3 0h1v4H9V7z" />
      </svg>
    ),
    package: (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M14.5 3l-6-2-6 2v9l6 2 6-2V3zm-6 9.5L3 10.7V4.3l5.5 1.8v6.4zm1-6.4l5.5-1.8v6.4l-5.5 1.8V6.1z" />
      </svg>
    ),
    trash: (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M6 2h4v1H6V2zM5 3v1H3v1h1v9a1 1 0 001 1h6a1 1 0 001-1V5h1V4h-2V3a1 1 0 00-1-1H6a1 1 0 00-1 1zm1 2h4v8H6V5z" />
      </svg>
    ),
    'file-zip': (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M10 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V4l-3-3zm-2 1h1v1H8V2zm0 2h1v1H8V4zm0 2h1v1H8V6zm0 2h1v2H8V8zM4 2h3v1H4v12h8V5h-2V2z" />
      </svg>
    ),
    'circuit-board': (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M2 2h12v12H2V2zm1 1v10h10V3H3zm2 2h2v2H5V5zm4 0h2v2H9V5zm-4 4h2v2H5V9zm4 0h2v2H9V9z" />
      </svg>
    ),
    'symbol-misc': (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 1a6 6 0 110 12A6 6 0 018 2zm0 2a1 1 0 100 2 1 1 0 000-2zm0 4a1 1 0 100 2 1 1 0 000-2zm-3-2a1 1 0 100 2 1 1 0 000-2zm6 0a1 1 0 100 2 1 1 0 000-2z" />
      </svg>
    ),
    eye: (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 4C4 4 1 8 1 8s3 4 7 4 7-4 7-4-3-4-7-4zm0 6a2 2 0 110-4 2 2 0 010 4z" />
      </svg>
    ),
    'symbol-constructor': (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 1l6 3v8l-6 3-6-3V4l6-3zm0 1.5L3.5 5v6L8 13.5l4.5-2.5V5L8 2.5z" />
      </svg>
    ),
    terminal: (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M2 3h12v10H2V3zm1 1v8h10V4H3zm1 1l3 2.5L4 10V5zm4 4h4v1H8V9z" />
      </svg>
    ),
    'new-file': (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M10 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V4l-3-3zm2 13H4V2h5v3h3v9zM8 6v2H6v1h2v2h1V9h2V8H9V6H8z" />
      </svg>
    ),
    checklist: (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M3.5 6L5 7.5 7.5 5l.7.7L5 9 2.8 6.7l.7-.7zM8 7h5v1H8V7zm0 3h5v1H8v-1z" />
      </svg>
    ),
    folder: (
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M2 3h5l1 1h6v9H2V3zm1 1v8h10V5H7.5l-1-1H3z" />
      </svg>
    ),
  };

  return icons[iconName] || (
    <svg viewBox="0 0 16 16" fill="currentColor">
      <circle cx="8" cy="8" r="6" />
    </svg>
  );
}

export function ActionButton({ icon, label, tooltip, onClick }: ActionButtonProps) {
  return (
    <button className="action-button" onClick={onClick} title={tooltip}>
      <span className="action-icon">{getIcon(icon)}</span>
      <span className="action-label">{label}</span>
    </button>
  );
}
