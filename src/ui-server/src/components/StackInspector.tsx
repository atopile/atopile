/**
 * Stack Inspector - IDE-like expandable stack trace viewer
 *
 * Displays structured tracebacks with:
 * - Expandable stack frames
 * - Local variable inspection
 * - Source code context
 */

import { useState } from 'react';
import './StackInspector.css';

interface LocalVar {
  type: string;
  repr: string;
  value?: unknown;
}

interface StackFrame {
  filename: string;
  lineno: number;
  function: string;
  code_line: string | null;
  locals: Record<string, LocalVar>;
}

export interface StructuredTraceback {
  exc_type: string;
  exc_message: string;
  frames: StackFrame[];
}

interface StackInspectorProps {
  traceback: StructuredTraceback;
}

/**
 * Truncate a file path to show only the last N segments
 */
function truncatePath(filename: string, segments: number = 2): string {
  const parts = filename.split('/');
  if (parts.length <= segments) return filename;
  return '.../' + parts.slice(-segments).join('/');
}

/**
 * Format a local variable value for display
 */
function formatValue(info: LocalVar): string {
  if (info.value !== undefined) {
    if (typeof info.value === 'string') {
      return `"${info.value}"`;
    }
    return String(info.value);
  }
  return info.repr;
}

export function StackInspector({ traceback }: StackInspectorProps) {
  // Default to expanding the most recent frame (last in list, which is index 0 when reversed)
  const [expandedFrames, setExpandedFrames] = useState<Set<number>>(() => {
    const initial = new Set<number>();
    if (traceback.frames.length > 0) {
      initial.add(traceback.frames.length - 1);
    }
    return initial;
  });

  const toggleFrame = (index: number) => {
    setExpandedFrames(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(index)) {
        newExpanded.delete(index);
      } else {
        newExpanded.add(index);
      }
      return newExpanded;
    });
  };

  const expandAll = () => {
    setExpandedFrames(new Set(traceback.frames.map((_, i) => i)));
  };

  const collapseAll = () => {
    setExpandedFrames(new Set());
  };

  if (!traceback.frames || traceback.frames.length === 0) {
    return (
      <div className="si-container">
        <div className="si-header">
          <span className="si-exc-type">{traceback.exc_type}</span>
          <span className="si-exc-message">{traceback.exc_message}</span>
        </div>
        <div className="si-empty">No stack frames available</div>
      </div>
    );
  }

  return (
    <div className="si-container">
      <div className="si-header">
        <div className="si-header-left">
          <span className="si-exc-type">{traceback.exc_type}</span>
          <span className="si-exc-message">{traceback.exc_message}</span>
        </div>
        <div className="si-header-actions">
          <button className="si-action-btn" onClick={expandAll} title="Expand all frames">
            +
          </button>
          <button className="si-action-btn" onClick={collapseAll} title="Collapse all frames">
            -
          </button>
        </div>
      </div>
      <div className="si-frames">
        {/* Display frames in reverse order (most recent first, like Python tracebacks) */}
        {[...traceback.frames].reverse().map((frame, reverseIndex) => {
          const originalIndex = traceback.frames.length - 1 - reverseIndex;
          const isExpanded = expandedFrames.has(originalIndex);
          const localCount = Object.keys(frame.locals).length;

          return (
            <div key={originalIndex} className={`si-frame ${isExpanded ? 'expanded' : ''}`}>
              <button
                className="si-frame-header"
                onClick={() => toggleFrame(originalIndex)}
              >
                <span className="si-arrow">{isExpanded ? '\u25BC' : '\u25B6'}</span>
                <span className="si-function">{frame.function}</span>
                <span className="si-location">
                  {truncatePath(frame.filename)}:{frame.lineno}
                </span>
                {localCount > 0 && (
                  <span className="si-local-count">{localCount} vars</span>
                )}
              </button>
              {isExpanded && (
                <div className="si-frame-content">
                  {frame.code_line && (
                    <pre className="si-code-line">{frame.code_line}</pre>
                  )}
                  {localCount > 0 && (
                    <div className="si-locals">
                      <div className="si-locals-header">Local Variables</div>
                      <table className="si-locals-table">
                        <tbody>
                          {Object.entries(frame.locals).map(([name, info]) => (
                            <tr key={name}>
                              <td className="si-var-name">{name}</td>
                              <td className="si-var-type">{info.type}</td>
                              <td className="si-var-value">{formatValue(info)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {localCount === 0 && !frame.code_line && (
                    <div className="si-no-info">No additional information</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
