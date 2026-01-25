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

// Recursive type for serialized values
interface SerializedValue {
  type: string;
  value?: unknown;  // primitives, or array of SerializedValue, or dict of SerializedValue
  repr?: string;    // for non-container types
  length?: number;  // for containers
  truncated?: boolean;
}

interface LocalVar extends SerializedValue {}

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
 * Check if a serialized value is a container type
 */
function isContainer(info: SerializedValue): boolean {
  return ['dict', 'list', 'tuple', 'set', 'frozenset'].includes(info.type);
}

/**
 * ContainerViewer - Recursive collapsible viewer for dicts, lists, sets
 */
function ContainerViewer({ value, name, depth = 0 }: { value: SerializedValue; name?: string; depth?: number }) {
  const [isExpanded, setIsExpanded] = useState(depth < 2);  // Auto-expand first 2 levels
  const isContainerType = isContainer(value);
  const maxDepth = 10;

  // For primitives or repr-only values, render inline
  if (!isContainerType || depth >= maxDepth) {
    const displayValue = value.repr ?? (
      value.value === null ? 'None' :
      typeof value.value === 'string' ? `"${value.value}"` :
      String(value.value)
    );

    return (
      <span className="cv-primitive">
        {name && <span className="cv-key">{name}: </span>}
        <span className="cv-type">{value.type}</span>
        <span className="cv-value">{displayValue}</span>
        {value.truncated && <span className="cv-truncated">…</span>}
      </span>
    );
  }

  // For containers, render collapsible
  const items = value.value as SerializedValue[] | Record<string, SerializedValue>;
  const isDict = value.type === 'dict';
  const itemCount = value.length ?? (Array.isArray(items) ? items.length : Object.keys(items).length);

  // Collapsed preview
  const brackets = isDict ? ['{', '}'] :
    value.type === 'set' || value.type === 'frozenset' ? ['{', '}'] :
    value.type === 'tuple' ? ['(', ')'] : ['[', ']'];

  const preview = `${brackets[0]}${itemCount} items${value.truncated ? '+' : ''}${brackets[1]}`;

  return (
    <div className={`cv-container cv-depth-${Math.min(depth, 5)}`}>
      <button className="cv-toggle" onClick={() => setIsExpanded(!isExpanded)}>
        {name && <span className="cv-key">{name}</span>}
        <span className="cv-type">{value.type}</span>
        <span className="cv-arrow">{isExpanded ? '▼' : '▶'}</span>
        {!isExpanded && <span className="cv-preview">{preview}</span>}
      </button>
      {isExpanded && (
        <div className="cv-children">
          {isDict ? (
            // Dict entries
            Object.entries(items as Record<string, SerializedValue>).map(([key, val]) => (
              <div key={key} className="cv-entry">
                <ContainerViewer value={val} name={key} depth={depth + 1} />
              </div>
            ))
          ) : (
            // Array/set entries
            (items as SerializedValue[]).map((item, idx) => (
              <div key={idx} className="cv-entry">
                <span className="cv-index">[{idx}]</span>
                <ContainerViewer value={item} depth={depth + 1} />
              </div>
            ))
          )}
          {value.truncated && (
            <div className="cv-truncated-notice">... {itemCount - (Array.isArray(items) ? items.length : Object.keys(items).length)} more items</div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Format a local variable value for display (simple inline version)
 */
function formatValueSimple(info: LocalVar): string {
  if (info.repr) return info.repr;
  if (info.value !== undefined) {
    if (typeof info.value === 'string') {
      return `"${info.value}"`;
    }
    return String(info.value);
  }
  return '<unknown>';
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
                      <div className="si-locals-list">
                        {Object.entries(frame.locals).map(([name, info]) => (
                          <div key={name} className="si-local-item">
                            {isContainer(info) ? (
                              <ContainerViewer value={info} name={name} depth={0} />
                            ) : (
                              <div className="si-local-simple">
                                <span className="si-var-name">{name}</span>
                                <span className="si-var-type">{info.type}</span>
                                <span className="si-var-value">{formatValueSimple(info)}</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
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
