/**
 * Log viewer component for displaying stage logs.
 */

import { useEffect, useRef, useState } from 'react';
import type { BuildStage } from '../types/build';
import { useBuildStore } from '../stores/buildStore';

interface LogViewerProps {
  buildName: string;
  stage: BuildStage;
}

type LogType = 'info' | 'error' | 'debug';

export function LogViewer({ buildName, stage }: LogViewerProps) {
  const { logContent, logLoading, logError, fetchLog } = useBuildStore();
  const [activeTab, setActiveTab] = useState<LogType>('info');
  const logRef = useRef<HTMLPreElement>(null);

  // Available log types for this stage
  const availableLogs: LogType[] = [];
  if (stage.log_files.info) availableLogs.push('info');
  if (stage.log_files.error) availableLogs.push('error');
  if (stage.log_files.debug) availableLogs.push('debug');

  // Set default tab based on available logs
  useEffect(() => {
    if (availableLogs.length > 0 && !availableLogs.includes(activeTab)) {
      setActiveTab(availableLogs[0]);
    }
  }, [stage.name]);

  // Fetch log when tab changes
  useEffect(() => {
    if (stage.log_files[activeTab]) {
      fetchLog(buildName, stage, activeTab);
    }
  }, [buildName, stage.name, activeTab, fetchLog]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logContent]);

  if (availableLogs.length === 0) {
    return (
      <div className="bg-panel-bg border border-panel-border rounded p-4">
        <p className="text-text-muted text-sm">No logs available for this stage.</p>
      </div>
    );
  }

  const tabColors: Record<LogType, string> = {
    info: 'text-text-primary',
    error: 'text-error',
    debug: 'text-text-muted',
  };

  // Get current log file path
  const currentLogPath = stage.log_files[activeTab];

  // Copy log path to clipboard
  const copyLogPath = () => {
    if (currentLogPath) {
      navigator.clipboard.writeText(currentLogPath);
    }
  };

  return (
    <div className="bg-panel-bg border border-panel-border rounded overflow-hidden flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-panel-border">
        {availableLogs.map((logType) => (
          <button
            key={logType}
            onClick={() => setActiveTab(logType)}
            className={`
              px-4 py-2 text-sm font-medium transition-colors
              ${activeTab === logType
                ? `${tabColors[logType]} border-b-2 border-accent bg-accent/10`
                : 'text-text-muted hover:text-text-primary'
              }
            `}
          >
            {logType.charAt(0).toUpperCase() + logType.slice(1)}
          </button>
        ))}
        <div className="flex-1" />
        <div className="flex items-center gap-2 px-4 py-2 text-xs text-text-muted">
          <span>{stage.name}</span>
          {currentLogPath && (
            <>
              <span className="text-panel-border">|</span>
              <button
                onClick={copyLogPath}
                className="hover:text-text-primary transition-colors flex items-center gap-1"
                title={`Click to copy: ${currentLogPath}`}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span className="font-mono">{currentLogPath.split('/').pop()}</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Log content */}
      <div className="flex-1 overflow-auto min-h-0">
        {logLoading ? (
          <div className="p-4 text-text-muted text-sm">Loading...</div>
        ) : logError ? (
          <div className="p-4 text-error text-sm">{logError}</div>
        ) : (
          <pre
            ref={logRef}
            className="p-4 text-xs font-mono text-text-primary whitespace-pre-wrap overflow-auto h-full"
          >
            {logContent || 'No content'}
          </pre>
        )}
      </div>
    </div>
  );
}
