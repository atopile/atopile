/**
 * Test Explorer Page Entry Point
 *
 * Standalone page combining TestExplorer + LogViewer for test discovery and execution.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom/client';
import { TestExplorer } from './components/TestExplorer';
import { TestLogViewer } from './components/TestLogViewer';
import { api } from './api/client';
import { connect, disconnect } from './api/websocket';
import { initializeTheme } from './hooks/useTheme';
import './index.css';
import './components/TestExplorer.css';

// Initialize theme before React renders to prevent flash
initializeTheme();

function TestExplorerPage() {
  // Connect to WebSocket on mount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, []);

  // Sidebar resize state
  const [sidebarWidth, setSidebarWidth] = useState(350);
  const isResizing = useRef(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizing.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      const newWidth = Math.min(Math.max(e.clientX, 200), 600);
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      if (isResizing.current) {
        isResizing.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  // Active test run ID for real-time log streaming
  const [activeTestRunId, setActiveTestRunId] = useState<string | null>(null);
  // Selected test name for viewing previous run logs
  const [selectedTestName, setSelectedTestName] = useState<string | null>(null);
  // Last run ID for the selected test
  const [lastRunId, setLastRunId] = useState<string | null>(null);

  // When a test run starts, show its logs
  const handleTestRunStart = useCallback((testRunId: string) => {
    setActiveTestRunId(testRunId);
    setSelectedTestName(null);
    setLastRunId(null);

    // Update URL with test_run_id for direct linking
    const url = new URL(window.location.href);
    url.searchParams.set('test_run_id', testRunId);
    url.searchParams.delete('test_name');
    window.history.replaceState({}, '', url.toString());
  }, []);

  // When a test is clicked, look up its last run and show logs
  const handleTestClick = useCallback(async (nodeId: string) => {
    // Always update selectedTestName to ensure UI reflects the click
    setSelectedTestName(nodeId);
    setActiveTestRunId(null);

    try {
      // Look up the last run for this test
      const result = await api.tests.lastRun(nodeId);
      if (result.found && result.test_run_id) {
        setLastRunId(result.test_run_id);
        // Update URL
        const url = new URL(window.location.href);
        url.searchParams.set('test_run_id', result.test_run_id);
        url.searchParams.set('test_name', nodeId);
        window.history.replaceState({}, '', url.toString());
      } else {
        setLastRunId(null);
        // Clear URL params
        const url = new URL(window.location.href);
        url.searchParams.delete('test_run_id');
        url.searchParams.set('test_name', nodeId);
        window.history.replaceState({}, '', url.toString());
      }
    } catch (error) {
      console.error('Failed to look up last test run:', error);
      setLastRunId(null);
    }
  }, []);

  // Determine which test_run_id to show in LogViewer
  const displayTestRunId = activeTestRunId || lastRunId;
  // Auto-stream whenever we have a test_run_id to display
  const shouldAutoStream = !!displayTestRunId;

  return (
    <div className="te-page">
      <div className="te-page-split">
        {/* Left: Test Explorer */}
        <div className="te-page-explorer" style={{ width: sidebarWidth }}>
          <TestExplorer
            onTestRunStart={handleTestRunStart}
            onTestClick={handleTestClick}
          />
        </div>

        {/* Resize handle */}
        <div
          className="te-resize-handle"
          onMouseDown={handleMouseDown}
        />

        {/* Right: Log Viewer or Placeholder */}
        <div className="te-page-logs">
          {displayTestRunId ? (
            <TestLogViewer
              testRunId={displayTestRunId}
              testName={selectedTestName}
              autoStream={shouldAutoStream}
            />
          ) : selectedTestName ? (
            <div className="te-page-placeholder">
              <div className="te-page-placeholder-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
              </div>
              <div>
                <strong>{selectedTestName.split('::').pop()}</strong>
              </div>
              <div>No previous runs found for this test.</div>
              <div style={{ fontSize: 'var(--font-size-xs)' }}>
                Select the test and click Run to execute it.
              </div>
            </div>
          ) : (
            <div className="te-page-placeholder">
              <div className="te-page-placeholder-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9 12l2 2 4-4" />
                </svg>
              </div>
              <div>Select a test to view its logs</div>
              <div style={{ fontSize: 'var(--font-size-xs)' }}>
                Or select tests and click Run to execute them
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Render the page
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <TestExplorerPage />
  </React.StrictMode>
);
