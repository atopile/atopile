/**
 * Test Explorer Component
 *
 * Discovers tests using pytest --collect-only, allows filtering,
 * multi-select, and execution with real-time log viewing.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';
import { sendActionWithResponse } from '../api/websocket';
import type { TestItem } from '../types/build';
import { EnvFlagsSelector } from './EnvFlagsSelector';
import './TestExplorer.css';

// Tree node structure for organizing tests
interface TestTreeNode {
  name: string;
  path: string;
  type: 'file' | 'class' | 'test';
  nodeId?: string;  // Only for test nodes
  children: TestTreeNode[];
  expanded: boolean;
}

interface TestExplorerProps {
  onTestRunStart?: (testRunId: string) => void;
  onTestClick?: (nodeId: string) => void;
}

// Build tree structure from flat test list
function buildTestTree(tests: TestItem[]): TestTreeNode[] {
  const fileMap = new Map<string, TestTreeNode>();

  for (const test of tests) {
    // Get or create file node
    if (!fileMap.has(test.file)) {
      fileMap.set(test.file, {
        name: test.file,
        path: test.file,
        type: 'file',
        children: [],
        expanded: true,
      });
    }
    const fileNode = fileMap.get(test.file)!;

    if (test.class_name) {
      // Find or create class node
      let classNode = fileNode.children.find(
        (c) => c.type === 'class' && c.name === test.class_name
      );
      if (!classNode) {
        classNode = {
          name: test.class_name,
          path: `${test.file}::${test.class_name}`,
          type: 'class',
          children: [],
          expanded: true,
        };
        fileNode.children.push(classNode);
      }

      // Add test to class
      classNode.children.push({
        name: test.method_name,
        path: test.node_id,
        type: 'test',
        nodeId: test.node_id,
        children: [],
        expanded: false,
      });
    } else {
      // Add test directly to file
      fileNode.children.push({
        name: test.method_name,
        path: test.node_id,
        type: 'test',
        nodeId: test.node_id,
        children: [],
        expanded: false,
      });
    }
  }

  // Sort files alphabetically
  return Array.from(fileMap.values()).sort((a, b) => a.name.localeCompare(b.name));
}

// Filter tree by search term
function filterTree(tree: TestTreeNode[], filter: string): TestTreeNode[] {
  if (!filter.trim()) return tree;

  const lowerFilter = filter.toLowerCase();

  function filterNode(node: TestTreeNode): TestTreeNode | null {
    // For test nodes, check if name matches
    if (node.type === 'test') {
      if (node.name.toLowerCase().includes(lowerFilter) ||
          node.path.toLowerCase().includes(lowerFilter)) {
        return node;
      }
      return null;
    }

    // For file/class nodes, filter children
    const filteredChildren = node.children
      .map(filterNode)
      .filter((c): c is TestTreeNode => c !== null);

    // Include node if it has matching children or its name matches
    if (filteredChildren.length > 0 ||
        node.name.toLowerCase().includes(lowerFilter)) {
      return {
        ...node,
        children: filteredChildren,
        expanded: true,  // Auto-expand when filtering
      };
    }

    return null;
  }

  return tree
    .map(filterNode)
    .filter((n): n is TestTreeNode => n !== null);
}

// Count total tests in tree
function countTests(tree: TestTreeNode[]): number {
  let count = 0;
  for (const node of tree) {
    if (node.type === 'test') {
      count++;
    } else {
      count += countTests(node.children);
    }
  }
  return count;
}

// Get all test node IDs from tree
function getAllTestIds(tree: TestTreeNode[]): string[] {
  const ids: string[] = [];
  for (const node of tree) {
    if (node.type === 'test' && node.nodeId) {
      ids.push(node.nodeId);
    } else {
      ids.push(...getAllTestIds(node.children));
    }
  }
  return ids;
}

// Icons
function PlayIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M23 4v6h-6M1 20v-6h6" />
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
    </svg>
  );
}

function ChevronIcon({ expanded, className }: { expanded: boolean; className?: string }) {
  return (
    <svg
      className={className}
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      style={{ transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.15s' }}
    >
      <polyline points="9 6 15 12 9 18" />
    </svg>
  );
}

function FileIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function ClassIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
    </svg>
  );
}

function TestIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

// Tree node component
function TreeNode({
  node,
  depth,
  selectedIds,
  onToggleExpand,
  onToggleSelect,
  onTestClick,
}: {
  node: TestTreeNode;
  depth: number;
  selectedIds: string[];
  onToggleExpand: (path: string) => void;
  onToggleSelect: (nodeId: string) => void;
  onTestClick?: (nodeId: string) => void;
}) {
  const isSelected = node.nodeId ? selectedIds.includes(node.nodeId) : false;
  const hasChildren = node.children.length > 0;

  // For file/class nodes, check if all children are selected
  const allChildrenSelected = node.type !== 'test' && node.children.length > 0 &&
    getAllTestIds([node]).every((id) => selectedIds.includes(id));
  const someChildrenSelected = node.type !== 'test' && node.children.length > 0 &&
    getAllTestIds([node]).some((id) => selectedIds.includes(id));

  const handleCheckboxChange = () => {
    if (node.nodeId) {
      onToggleSelect(node.nodeId);
    } else {
      // Toggle all children
      const childIds = getAllTestIds([node]);
      if (allChildrenSelected) {
        // Deselect all
        childIds.forEach((id) => {
          if (selectedIds.includes(id)) {
            onToggleSelect(id);
          }
        });
      } else {
        // Select all
        childIds.forEach((id) => {
          if (!selectedIds.includes(id)) {
            onToggleSelect(id);
          }
        });
      }
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (node.type === 'test' && node.nodeId && onTestClick) {
      onTestClick(node.nodeId);
    } else if (hasChildren) {
      onToggleExpand(node.path);
    }
  };

  const Icon = node.type === 'file' ? FileIcon :
               node.type === 'class' ? ClassIcon : TestIcon;

  return (
    <>
      <div
        className={`te-tree-node te-tree-${node.type} ${isSelected ? 'selected' : ''}`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={handleClick}
      >
        {hasChildren && (
          <button
            className="te-tree-toggle"
            onClick={(e) => { e.stopPropagation(); onToggleExpand(node.path); }}
          >
            <ChevronIcon expanded={node.expanded} />
          </button>
        )}
        {!hasChildren && <span className="te-tree-toggle-placeholder" />}

        <input
          type="checkbox"
          className="te-tree-checkbox"
          checked={node.type === 'test' ? isSelected : allChildrenSelected}
          ref={(el) => {
            if (el && node.type !== 'test') {
              el.indeterminate = someChildrenSelected && !allChildrenSelected;
            }
          }}
          onChange={handleCheckboxChange}
          onClick={(e) => e.stopPropagation()}
        />

        <Icon className="te-tree-icon" />
        <span className="te-tree-name">{node.name}</span>

        {node.type !== 'test' && (
          <span className="te-tree-count">{countTests([node])}</span>
        )}
      </div>

      {hasChildren && node.expanded && (
        <div className="te-tree-children">
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedIds={selectedIds}
              onToggleExpand={onToggleExpand}
              onToggleSelect={onToggleSelect}
              onTestClick={onTestClick}
            />
          ))}
        </div>
      )}
    </>
  );
}

export function TestExplorer({ onTestRunStart, onTestClick }: TestExplorerProps) {
  // Store state
  const isConnected = useStore((state) => state.isConnected);
  const collectedTests = useStore((state) => state.collectedTests);
  const isLoadingTests = useStore((state) => state.isLoadingTests);
  const testsError = useStore((state) => state.testsError);
  const testCollectionErrors = useStore((state) => state.testCollectionErrors);
  const selectedTestNodeIds = useStore((state) => state.selectedTestNodeIds);
  const testRun = useStore((state) => state.testRun);
  const testFilter = useStore((state) => state.testFilter);
  const testPaths = useStore((state) => state.testPaths);
  const testMarkers = useStore((state) => state.testMarkers);

  const {
    setCollectedTests,
    setLoadingTests,
    setTestsError,
    setTestCollectionErrors,
    setTestFilter,
    setTestPaths,
    setTestMarkers,
    toggleTestSelected,
    selectAllTests,
    clearTestSelection,
    startTestRun,
    completeTestRun,
  } = useStore.getState();

  // Local state for tree expansion
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

  // Environment variables for test runs (persisted to localStorage)
  const [envVars, setEnvVars] = useState<Record<string, string>>(() => {
    try {
      const stored = localStorage.getItem('te-envVars');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (typeof parsed === 'object' && parsed !== null) {
          return parsed;
        }
      }
    } catch { /* ignore */ }
    return {};
  });

  // Persist envVars to localStorage
  useEffect(() => {
    localStorage.setItem('te-envVars', JSON.stringify(envVars));
  }, [envVars]);

  // Build and filter tree
  const testTree = useMemo(() => {
    const tree = buildTestTree(collectedTests);
    // Initialize expanded state
    const paths = new Set<string>();
    function collectPaths(nodes: TestTreeNode[]) {
      for (const node of nodes) {
        if (node.expanded) paths.add(node.path);
        collectPaths(node.children);
      }
    }
    collectPaths(tree);
    return tree;
  }, [collectedTests]);

  // Apply expansion state to tree
  const treeWithExpansion = useMemo(() => {
    function applyExpansion(nodes: TestTreeNode[]): TestTreeNode[] {
      return nodes.map((node) => ({
        ...node,
        expanded: expandedPaths.has(node.path),
        children: applyExpansion(node.children),
      }));
    }
    return applyExpansion(testTree);
  }, [testTree, expandedPaths]);

  const filteredTree = useMemo(
    () => filterTree(treeWithExpansion, testFilter),
    [treeWithExpansion, testFilter]
  );

  const totalTests = countTests(testTree);
  const filteredTestCount = countTests(filteredTree);

  // Initialize expansion on first load
  useEffect(() => {
    if (collectedTests.length > 0 && expandedPaths.size === 0) {
      const paths = new Set<string>();
      function collectPaths(nodes: TestTreeNode[]) {
        for (const node of nodes) {
          if (node.type !== 'test') paths.add(node.path);
          collectPaths(node.children);
        }
      }
      collectPaths(testTree);
      setExpandedPaths(paths);
    }
  }, [collectedTests, testTree, expandedPaths.size]);

  // Collect tests
  const handleCollect = useCallback(async () => {
    setLoadingTests(true);
    setTestsError(null);
    setTestCollectionErrors({});

    try {
      const response = await api.tests.collect(testPaths, '', testMarkers);
      if (response.success) {
        setCollectedTests(response.tests);
        setTestCollectionErrors(response.errors);
        // Reset expansion to show all
        const paths = new Set<string>();
        const tree = buildTestTree(response.tests);
        function collectPaths(nodes: TestTreeNode[]) {
          for (const node of nodes) {
            if (node.type !== 'test') paths.add(node.path);
            collectPaths(node.children);
          }
        }
        collectPaths(tree);
        setExpandedPaths(paths);
      } else {
        setTestsError(response.error || 'Failed to collect tests');
      }
    } catch (error) {
      setTestsError(error instanceof Error ? error.message : 'Failed to collect tests');
    } finally {
      setLoadingTests(false);
    }
  }, [testPaths, testMarkers]);

  // Run selected tests
  const handleRun = useCallback(async () => {
    if (selectedTestNodeIds.length === 0) return;
    if (!isConnected) {
      setTestsError('Not connected to server. Please wait for connection...');
      return;
    }

    try {
      const result = await sendActionWithResponse('runTests', {
        testNodeIds: selectedTestNodeIds,
        pytestArgs: '',
        env: Object.keys(envVars).length > 0 ? envVars : undefined,
      });

      if (result.result?.success && result.result?.test_run_id) {
        const testRunId = result.result.test_run_id as string;
        startTestRun(testRunId);
        onTestRunStart?.(testRunId);

        // Mark as complete after a delay (in real implementation, would track actual completion)
        setTimeout(() => {
          completeTestRun();
        }, 1000);
      }
    } catch (error) {
      console.error('Failed to run tests:', error);
      setTestsError(error instanceof Error ? error.message : 'Failed to run tests');
    }
  }, [selectedTestNodeIds, onTestRunStart, isConnected, setTestsError, envVars]);

  // Toggle node expansion
  const handleToggleExpand = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  // Handle test click for viewing logs
  const handleTestClick = useCallback(async (nodeId: string) => {
    onTestClick?.(nodeId);
  }, [onTestClick]);

  // Auto-collect on mount
  useEffect(() => {
    if (collectedTests.length === 0) {
      handleCollect();
    }
  }, []);

  const hasErrors = Object.keys(testCollectionErrors).length > 0;

  return (
    <div className="te-container">
      {/* Toolbar */}
      <div className="te-toolbar">
        <div className="te-toolbar-row">
          <input
            type="text"
            className="te-input te-search"
            placeholder="Filter tests..."
            value={testFilter}
            onChange={(e) => setTestFilter(e.target.value)}
          />
          <button
            className="te-btn te-btn-icon"
            onClick={handleCollect}
            disabled={isLoadingTests}
            title="Refresh tests"
          >
            <RefreshIcon className={isLoadingTests ? 'te-spin' : ''} />
          </button>
        </div>

        <div className="te-toolbar-row te-toolbar-secondary">
          <input
            type="text"
            className="te-input te-input-small"
            placeholder="Paths (e.g., test src)"
            value={testPaths}
            onChange={(e) => setTestPaths(e.target.value)}
            title="Space-separated paths to search"
          />
          <input
            type="text"
            className="te-input te-input-small"
            placeholder="Markers (-m)"
            value={testMarkers}
            onChange={(e) => setTestMarkers(e.target.value)}
            title="Pytest marker expression"
          />
        </div>

        <div className="te-toolbar-row te-toolbar-actions">
          {/* Connection status */}
          <div className={`te-connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="te-connection-dot" />
            <span className="te-connection-label">{isConnected ? 'Connected' : 'Connecting...'}</span>
          </div>

          <div className="te-selection-info">
            {selectedTestNodeIds.length > 0 ? (
              <>
                <span className="te-selection-count">{selectedTestNodeIds.length}</span>
                <span> of {totalTests} selected</span>
                <button className="te-btn-link" onClick={clearTestSelection}>Clear</button>
              </>
            ) : (
              <>
                <span>{filteredTestCount}</span>
                {testFilter && <span> of {totalTests}</span>}
                <span> tests</span>
                {totalTests > 0 && (
                  <button className="te-btn-link" onClick={selectAllTests}>Select all</button>
                )}
              </>
            )}
          </div>

          <EnvFlagsSelector
            envVars={envVars}
            onEnvVarsChange={setEnvVars}
          />

          <button
            className="te-btn te-btn-primary"
            onClick={handleRun}
            disabled={!isConnected || selectedTestNodeIds.length === 0 || testRun.isRunning}
            title={!isConnected ? 'Not connected to server' : `Run ${selectedTestNodeIds.length} selected tests`}
          >
            <PlayIcon />
            <span>Run{selectedTestNodeIds.length > 0 ? ` (${selectedTestNodeIds.length})` : ''}</span>
          </button>
        </div>
      </div>

      {/* Error display */}
      {testsError && (
        <div className="te-error">
          <span className="te-error-icon">!</span>
          <span>{testsError}</span>
        </div>
      )}

      {/* Collection errors */}
      {hasErrors && (
        <div className="te-collection-errors">
          <div className="te-collection-errors-header">
            Collection errors ({Object.keys(testCollectionErrors).length})
          </div>
          {Object.entries(testCollectionErrors).map(([file, error]) => (
            <details key={file} className="te-collection-error">
              <summary>{file}</summary>
              <pre>{error}</pre>
            </details>
          ))}
        </div>
      )}

      {/* Tree view */}
      <div className="te-tree">
        {isLoadingTests ? (
          <div className="te-loading">
            <div className="te-loading-spinner" />
            <span>Collecting tests...</span>
          </div>
        ) : filteredTree.length === 0 ? (
          <div className="te-empty">
            {testFilter ? (
              <span>No tests match "{testFilter}"</span>
            ) : (
              <span>No tests found. Click refresh to collect tests.</span>
            )}
          </div>
        ) : (
          filteredTree.map((node) => (
            <TreeNode
              key={node.path}
              node={node}
              depth={0}
              selectedIds={selectedTestNodeIds}
              onToggleExpand={handleToggleExpand}
              onToggleSelect={toggleTestSelected}
              onTestClick={handleTestClick}
            />
          ))
        )}
      </div>
    </div>
  );
}
