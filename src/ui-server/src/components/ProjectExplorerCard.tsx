/**
 * ProjectExplorerCard - Displays module structure per build target.
 * Provides a top-level explorer view separate from builds.
 */

import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, GitBranch, Circle } from 'lucide-react';
import type { BuildTarget } from './projectsTypes';
import type { ModuleChild } from '../types/build';
import { ModuleTree } from './ModuleTreeNode';
import { sendActionWithResponse } from '../api/websocket';
import './ProjectExplorerCard.css';

interface ProjectExplorerCardProps {
  builds: BuildTarget[];
  projectRoot: string;
  defaultExpanded?: boolean;
}

type TargetState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; children: ModuleChild[] };

const getTargetKey = (build: BuildTarget) => `${build.id}:${build.entry ?? ''}`;

export function ProjectExplorerCard({ builds, projectRoot, defaultExpanded = true }: ProjectExplorerCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [expandedTargets, setExpandedTargets] = useState<Set<string>>(new Set());
  const [targetStates, setTargetStates] = useState<Record<string, TargetState>>({});

  const targetKeys = useMemo(() => {
    const keys = new Map<string, string>();
    builds.forEach((build) => {
      keys.set(build.id, getTargetKey(build));
    });
    return keys;
  }, [builds]);

  const fetchChildren = (build: BuildTarget) => {
    const key = getTargetKey(build);
    if (!projectRoot || !build.entry) return;

    setTargetStates(prev => ({
      ...prev,
      [key]: { status: 'loading' }
    }));

    sendActionWithResponse('getModuleChildren', {
      projectRoot,
      entryPoint: build.entry,
      maxDepth: 5,
    })
      .then((response) => {
        const result = response.result ?? {};
        const children = Array.isArray((result as { children?: unknown }).children)
          ? (result as { children: ModuleChild[] }).children
          : [];
        setTargetStates(prev => ({
          ...prev,
          [key]: { status: 'ready', children }
        }));
      })
      .catch((err) => {
        setTargetStates(prev => ({
          ...prev,
          [key]: { status: 'error', error: err.message || 'Failed to load module structure' }
        }));
      });
  };

  useEffect(() => {
    if (!expanded || !projectRoot) return;

    builds.forEach((build) => {
      if (!expandedTargets.has(build.id)) return;
      if (!build.entry) return;

      const key = getTargetKey(build);
      const state = targetStates[key];
      if (!state || state.status === 'idle') {
        fetchChildren(build);
      }
    });
  }, [expanded, builds, expandedTargets, projectRoot, targetStates]);

  // Don't render if no builds - but still show header when loading could provide builds
  if (!builds || builds.length === 0) {
    return null;
  }

  return (
    <div className="project-explorer-card" onClick={(e) => e.stopPropagation()}>
      <div
        className="project-explorer-card-header"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
      >
        <span className="project-explorer-card-expand">
          <ChevronDown
            size={12}
            className={`expand-icon ${expanded ? 'expanded' : ''}`}
          />
        </span>
        <GitBranch size={14} className="project-explorer-card-icon" />
        <span className="project-explorer-card-title">Explorer</span>
        <span className="project-explorer-count">{builds.length}</span>
      </div>

      {expanded && (
        <div className="project-explorer-card-content">
          {builds.map((build) => {
            const isTargetExpanded = expandedTargets.has(build.id);
            const key = targetKeys.get(build.id) ?? getTargetKey(build);
            const state = targetStates[key] ?? { status: 'idle' };
            const moduleName = build.entry?.split(':').pop() || build.name;

            return (
              <div key={build.id} className="project-explorer-target">
                <div
                  className="project-explorer-target-header"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedTargets(prev => {
                      const next = new Set(prev);
                      if (next.has(build.id)) {
                        next.delete(build.id);
                      } else {
                        next.add(build.id);
                      }
                      return next;
                    });
                  }}
                >
                  <span className="project-explorer-target-expand">
                    {isTargetExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  </span>
                  <span className="project-explorer-target-name">{build.name}</span>
                  {build.entry && (
                    <span className="project-explorer-target-entry" title={build.entry}>
                      {moduleName}
                    </span>
                  )}
                </div>

                {isTargetExpanded && (
                  <div className="project-explorer-target-body">
                    {!build.entry && (
                      <div className="project-explorer-empty">No entry point</div>
                    )}
                    {build.entry && state.status === 'loading' && (
                      <div className="project-explorer-loading">
                        <Circle size={12} className="spinner" />
                        <span>Loading module structure...</span>
                      </div>
                    )}
                    {build.entry && state.status === 'error' && (
                      <div className="project-explorer-error">{state.error}</div>
                    )}
                    {build.entry && state.status === 'ready' && (
                      state.children.length > 0 ? (
                        <ModuleTree
                          children={state.children}
                          rootName={moduleName}
                        />
                      ) : (
                        <div className="project-explorer-empty">No module structure found</div>
                      )
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
