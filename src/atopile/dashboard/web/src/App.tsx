/**
 * Main dashboard application component.
 */

import { useEffect } from 'react';
import { useBuildStore } from './stores/buildStore';
import { BuildTabs } from './components/BuildTabs';
import { BuildSummary } from './components/BuildSummary';
import { StageTable } from './components/StageTable';
import { LogViewer } from './components/LogViewer';

function Header() {
  const { lastUpdated, isPolling, isConnected } = useBuildStore();

  return (
    <header className="bg-panel-bg border-b border-panel-border px-4 py-2 flex items-center justify-between">
      <h1 className="text-lg font-bold text-text-primary">atopile Build Dashboard</h1>
      <div className="flex items-center gap-3 text-xs text-text-muted">
        {isPolling && (
          <span className="flex items-center gap-1">
            {isConnected ? (
              <>
                <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                Live
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-text-muted" />
                Disconnected
              </>
            )}
          </span>
        )}
        {lastUpdated && (
          <span>Updated: {lastUpdated.toLocaleTimeString()}</span>
        )}
      </div>
    </header>
  );
}

function MainContent() {
  const { summary, getSelectedBuild, getSelectedStage } = useBuildStore();

  if (!summary || summary.builds.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-text-muted text-lg mb-2">No builds available</p>
          <p className="text-text-muted text-sm">Waiting for build data...</p>
        </div>
      </div>
    );
  }

  const selectedBuild = getSelectedBuild();
  const selectedStage = getSelectedStage();

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Build tabs along the top */}
      <div className="border-b border-panel-border bg-panel-bg">
        <BuildTabs builds={summary.builds} />
      </div>

      {/* Main content area */}
      <main className="flex-1 flex min-h-0 p-3 gap-3">
        {selectedBuild ? (
          <>
            {/* Left panel: Summary + Stages (narrower) */}
            <div className="w-80 flex flex-col gap-3 overflow-y-auto flex-shrink-0">
              <BuildSummary build={selectedBuild} />
              <StageTable build={selectedBuild} />
            </div>

            {/* Right panel: Log viewer (takes remaining space) */}
            <div className="flex-1 flex flex-col min-w-0 min-h-0">
              {selectedStage ? (
                <LogViewer buildName={selectedBuild.name} stage={selectedStage} />
              ) : (
                <div className="bg-panel-bg border border-panel-border rounded p-4 flex-1 flex items-center justify-center">
                  <p className="text-text-muted text-sm">Select a stage to view logs</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-text-muted">Select a build from the tabs above</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default function App() {
  const { startPolling, stopPolling } = useBuildStore();

  useEffect(() => {
    // Start polling when component mounts
    startPolling(500);

    // Stop polling when component unmounts
    return () => {
      stopPolling();
    };
  }, [startPolling, stopPolling]);

  return (
    <div className="h-screen flex flex-col bg-dashboard-bg">
      <Header />
      <MainContent />
    </div>
  );
}
