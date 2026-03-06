import type { Build, QueuedBuild } from '../../types/build';
import type { AgentMessage, AgentTraceView } from '../state/types';
import type { MessageBuildStatusState } from './shared';

interface BuildRunReferences {
  hasBuildRun: boolean;
  hasRunningBuildRun: boolean;
  buildIds: string[];
  targets: string[];
}

function extractBuildRunReferences(traces: AgentTraceView[]): BuildRunReferences {
  const buildIds: string[] = [];
  const targets: string[] = [];
  const seenBuildIds = new Set<string>();
  const seenTargets = new Set<string>();
  let hasBuildRun = false;
  let hasRunningBuildRun = false;

  const addBuildId = (value: unknown) => {
    if (typeof value !== 'string') return;
    const trimmed = value.trim();
    if (!trimmed || seenBuildIds.has(trimmed)) return;
    seenBuildIds.add(trimmed);
    buildIds.push(trimmed);
  };

  const addTarget = (value: unknown) => {
    if (typeof value !== 'string') return;
    const trimmed = value.trim();
    if (!trimmed || seenTargets.has(trimmed)) return;
    seenTargets.add(trimmed);
    targets.push(trimmed);
  };

  for (const trace of traces) {
    if (trace.name !== 'build_run') continue;
    hasBuildRun = true;
    if (trace.running) hasRunningBuildRun = true;

    addBuildId(trace.result.build_id);
    addBuildId(trace.result.buildId);
    addTarget(trace.result.target);
    addTarget(trace.result.build_target);

    const candidateGroups = [trace.result.build_targets, trace.result.buildTargets];
    for (const group of candidateGroups) {
      if (!Array.isArray(group)) continue;
      for (const row of group) {
        if (!row || typeof row !== 'object') continue;
        const candidate = row as Record<string, unknown>;
        addBuildId(candidate.build_id);
        addBuildId(candidate.buildId);
        addTarget(candidate.target);
      }
    }

    if (Array.isArray(trace.args.targets)) {
      for (const target of trace.args.targets) {
        addTarget(target);
      }
    }
  }

  return { hasBuildRun, hasRunningBuildRun, buildIds, targets };
}

function buildStatusRank(status: string): number {
  if (status === 'building') return 0;
  if (status === 'queued') return 1;
  if (status === 'failed') return 2;
  if (status === 'warning') return 3;
  if (status === 'success') return 4;
  if (status === 'cancelled') return 5;
  return 6;
}

function sortBuildsForChat(left: Build, right: Build): number {
  const statusDiff = buildStatusRank(left.status) - buildStatusRank(right.status);
  if (statusDiff !== 0) return statusDiff;

  const leftStarted = typeof left.startedAt === 'number' ? left.startedAt : 0;
  const rightStarted = typeof right.startedAt === 'number' ? right.startedAt : 0;
  if (leftStarted !== rightStarted) return rightStarted - leftStarted;

  return (left.target || left.name || '').localeCompare(right.target || right.name || '');
}

function normalizeQueuedBuild(build: Build, projectRoot: string): QueuedBuild | null {
  if (typeof build.buildId !== 'string' || !build.buildId) return null;
  const status = build.status as QueuedBuild['status'];
  const validStatuses: QueuedBuild['status'][] = ['queued', 'building', 'success', 'failed', 'warning', 'cancelled'];
  if (!validStatuses.includes(status)) return null;

  return {
    buildId: build.buildId,
    status,
    projectRoot: build.projectRoot || projectRoot,
    target: build.target || build.name || 'default',
    entry: build.entry,
    startedAt: typeof build.startedAt === 'number' ? build.startedAt : 0,
    elapsedSeconds: build.elapsedSeconds,
    stages: Array.isArray(build.stages)
      ? build.stages.map((stage) => ({
          name: stage.name,
          stageId: stage.stageId,
          displayName: stage.displayName,
          status: stage.status,
          elapsedSeconds: stage.elapsedSeconds,
        }))
      : undefined,
    totalStages: build.totalStages,
    error: build.error,
  };
}

function resolveBuildStatusForTraces(
  traces: AgentTraceView[],
  projectBuilds: Build[],
  projectRoot: string,
): Omit<MessageBuildStatusState, 'messageId'> | null {
  const references = extractBuildRunReferences(traces);
  if (!references.hasBuildRun) return null;

  const buildsById = new Map<string, Build>();
  for (const build of projectBuilds) {
    if (typeof build.buildId !== 'string' || !build.buildId) continue;
    buildsById.set(build.buildId, build);
  }

  const targetSet = new Set(references.targets);
  const selected: Build[] = [];
  const selectedIds = new Set<string>();
  const addBuild = (build: Build) => {
    const buildId = typeof build.buildId === 'string' ? build.buildId : null;
    if (!buildId || selectedIds.has(buildId)) return;
    selectedIds.add(buildId);
    selected.push(build);
  };

  for (const buildId of references.buildIds) {
    const matched = buildsById.get(buildId);
    if (matched) addBuild(matched);
  }

  if (targetSet.size > 0) {
    for (const build of projectBuilds) {
      if (!targetSet.has(build.target || '')) continue;
      addBuild(build);
    }
  }

  if (selected.length === 0 && references.hasRunningBuildRun) {
    for (const build of projectBuilds) {
      if (build.status === 'queued' || build.status === 'building') {
        addBuild(build);
      }
    }
  }

  selected.sort(sortBuildsForChat);
  const builds = selected
    .map((build) => normalizeQueuedBuild(build, projectRoot))
    .filter((build): build is QueuedBuild => Boolean(build));

  const matchedBuildIds = new Set(builds.map((build) => build.buildId));
  const pendingBuildIds = references.buildIds.filter((buildId) => !matchedBuildIds.has(buildId));

  return {
    builds,
    pendingBuildIds,
  };
}

export function findLatestBuildStatus(
  messages: AgentMessage[],
  projectBuilds: Build[],
  projectRoot: string | null,
): MessageBuildStatusState | null {
  if (!projectRoot) return null;

  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role !== 'assistant' || !message.toolTraces || message.toolTraces.length === 0) {
      continue;
    }
    const resolved = resolveBuildStatusForTraces(message.toolTraces, projectBuilds, projectRoot);
    if (!resolved) continue;
    return {
      messageId: message.id,
      builds: resolved.builds,
      pendingBuildIds: resolved.pendingBuildIds,
    };
  }

  return null;
}
