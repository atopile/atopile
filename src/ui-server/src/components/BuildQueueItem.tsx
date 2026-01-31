/**
 * BuildQueueItem - Expandable build queue item component
 * Shows build status, stages, and allows log viewing
 */

import { useState, useMemo, useEffect, useRef } from 'react'
import { ChevronDown, X, CheckCircle2, XCircle, AlertCircle, AlertTriangle } from 'lucide-react'
import type { QueuedBuild } from '../types/build'
import { useStore } from '../store'
import { sendAction } from '../api/websocket'
import { postMessage } from '../api/vscodeApi'
import { StatusIcon } from './StatusIcon'

// Track recently completed builds for animation
const recentlyCompletedBuilds = new Set<string>()

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return ''
  if (seconds < 1) {
    return `${seconds.toFixed(2)}s`
  }
  if (seconds < 10) {
    return `${seconds.toFixed(1)}s`
  }
  const total = Math.floor(seconds)
  if (total < 60) {
    return `${total}s`
  }
  const mins = Math.floor(total / 60)
  const secs = total % 60
  if (mins < 60) {
    return `${mins}m ${secs}s`
  }
  const hours = Math.floor(mins / 60)
  const remainMins = mins % 60
  return `${hours}h ${remainMins}m`
}

function formatRelativeSeconds(epochSeconds: number): string {
  if (!Number.isFinite(epochSeconds) || epochSeconds <= 0) return ''
  const diffMs = Date.now() - epochSeconds * 1000
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return new Date(epochSeconds * 1000).toLocaleDateString()
}

function getBuildCounter(buildId?: string): string | null {
  if (!buildId) return null
  const match = buildId.match(/^build-(\d+)-/)
  if (match) return `#${match[1]}`
  return `#${buildId}`
}

// Build status icon component
function BuildStatusIcon({ status }: { status: QueuedBuild['status'] }) {
  switch (status) {
    case 'success':
      return <CheckCircle2 size={14} className="status-icon success" />
    case 'failed':
      return <XCircle size={14} className="status-icon failed" />
    case 'warning':
      return <AlertTriangle size={14} className="status-icon warning" />
    case 'cancelled':
      return <AlertCircle size={14} className="status-icon cancelled" />
    default:
      return null
  }
}

// Stage status icon component - uses unified StatusIcon for consistency
function StageStatusIcon({ status }: { status: string }) {
  // Map to StatusIcon component for consistent styling across the app
  return <StatusIcon status={status as any} size={12} />
}

function getCurrentStage(build: QueuedBuild): { name: string } | null {
  if (!build.stages || build.stages.length === 0) return null

  const running = build.stages.find(
    (stage) => stage.status === 'running' || stage.status === 'building'
  )
  if (running) {
    return { name: running.displayName || running.name }
  }

  const completed = [...build.stages].reverse().find((stage) =>
    stage.status === 'success' ||
    stage.status === 'warning' ||
    stage.status === 'failed' ||
    stage.status === 'error'
  )

  if (completed) {
    return { name: completed.displayName || completed.name }
  }

  return null
}

interface BuildQueueItemProps {
  build: QueuedBuild
  onCancel?: (buildId: string) => void
}

export function BuildQueueItem({
  build,
  onCancel,
}: BuildQueueItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [justCompleted, setJustCompleted] = useState(false)
  const prevStatusRef = useRef<string | null>(null)

  // Track when build transitions from building to complete for animation
  useEffect(() => {
    const prevStatus = prevStatusRef.current
    const currentStatus = build.status
    const isNowComplete = currentStatus === 'success' || currentStatus === 'failed' || currentStatus === 'warning'
    const wasBuilding = prevStatus === 'building' || prevStatus === 'queued'

    // If just transitioned to complete, trigger animation
    if (wasBuilding && isNowComplete && build.buildId && !recentlyCompletedBuilds.has(build.buildId)) {
      recentlyCompletedBuilds.add(build.buildId)
      setJustCompleted(true)

      // Remove animation class after animation completes
      const timer = setTimeout(() => {
        setJustCompleted(false)
        // Clean up old build IDs after a while to prevent memory leak
        setTimeout(() => {
          recentlyCompletedBuilds.delete(build.buildId)
        }, 5000)
      }, 600)

      return () => clearTimeout(timer)
    }

    prevStatusRef.current = currentStatus
  }, [build.status, build.buildId])

  // Calculate progress from stages
  const progress = useMemo(() => {
    if (!build.stages || build.stages.length === 0) return 0
    const completedStages = build.stages.filter(
      (s) => s.status === 'success' || s.status === 'warning'
    ).length
    // Use actual totalStages from backend, or fall back to completed + 1 to avoid 100%
    const totalStages = build.totalStages || Math.max(completedStages + 1, 10)
    return Math.round((completedStages / totalStages) * 100)
  }, [build.stages, build.totalStages])

  const targetName = build.target || build.entry || 'default'
  const isComplete = build.status === 'success' || build.status === 'failed' || build.status === 'cancelled' || build.status === 'warning'
  const hasStages = build.stages && build.stages.length > 0
  // Check if any stage has failed - used to hide progress bar even if build status hasn't updated yet
  const hasFailedStage = build.stages?.some(s => s.status === 'failed' || s.status === 'error') ?? false
  const canExpand = true
  const buildCounter = useMemo(() => getBuildCounter(build.buildId), [build.buildId])
  const currentStage = useMemo(() => getCurrentStage(build), [build])

  const elapsed = build.elapsedSeconds ?? 0

  const totalDuration = build.elapsedSeconds ?? null

  const runningStageElapsed = useMemo(() => {
    if (!build.stages || build.stages.length === 0) return null
    const running = build.stages.find((stage) => stage.status === 'running')
    return running?.elapsedSeconds ?? null
  }, [build.stages])

  const completedAt = useMemo(() => {
    if (!build.startedAt) return null
    if (build.elapsedSeconds && build.elapsedSeconds > 0) {
      return build.startedAt + build.elapsedSeconds
    }
    return null
  }, [build.startedAt, build.elapsedSeconds])

  const statusLabel = useMemo(() => {
    switch (build.status) {
      case 'queued':
        return 'Queued'
      case 'building':
        return ''
      case 'success':
      case 'failed':
      case 'warning':
      case 'cancelled':
        return completedAt ? formatRelativeSeconds(completedAt) : ''
      default:
        return build.status
    }
  }, [build.status, completedAt])

  const elapsedLabel = useMemo(() => {
    if (build.status !== 'queued' && build.status !== 'building') return ''
    if (elapsed > 0) return formatDuration(elapsed)
    return '0s'
  }, [build.status, elapsed])

  return (
    <div className={`build-queue-item ${build.status} ${isExpanded ? 'expanded' : ''} ${justCompleted ? 'just-completed' : ''}`}>
      <div
        className="build-queue-header"
        onClick={() => {
          if (canExpand) setIsExpanded(!isExpanded)
          if (build.buildId) {
            useStore.getState().setLogViewerBuildId(build.buildId)
            sendAction('setLogViewCurrentId', { buildId: build.buildId, stage: null })
            postMessage({ type: 'showBuildLogs' })
          }
        }}
      >
        {canExpand && (
          <ChevronDown
            size={10}
            className={`build-expand-icon ${isExpanded ? 'open' : ''}`}
          />
        )}
        {isComplete ? (
          <BuildStatusIcon status={build.status} />
        ) : hasFailedStage ? (
          <BuildStatusIcon status="failed" />
        ) : build.status === 'building' ? (
          <StatusIcon status="building" size={14} />
        ) : null}
        <div className="build-queue-info">
          <span className="build-queue-target">{targetName}</span>
          {build.status === 'building' && !hasFailedStage && currentStage && (
            <span className="build-queue-stage" title={currentStage.name}>
              {currentStage.name}
            </span>
          )}
          {build.status === 'failed' && (
            <span className="build-failed-hint">
              Build failed... <span className="show-logs-link">show logs</span>
            </span>
          )}
        </div>
        {statusLabel && (
          <div className="build-queue-meta">
            <span className="build-queue-status">{statusLabel}</span>
            {elapsedLabel && (
              <span className="build-queue-time">{elapsedLabel}</span>
            )}
          </div>
        )}
        {build.status === 'building' && !hasFailedStage && (
          <div className="build-queue-progress">
            <div
              className="build-queue-progress-bar"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
        {(build.status === 'queued' || build.status === 'building') && onCancel && build.buildId && (
          <button
            className="build-queue-cancel"
            onClick={(e) => {
              e.stopPropagation()
              onCancel(build.buildId)
            }}
            title="Cancel build"
          >
            <X size={10} />
          </button>
        )}
      </div>

      {/* Expanded stages view */}
      {isExpanded && (
        <div className="build-stages">
          <div className="build-stages-header">
            <span className="build-stages-title">Steps ({build.stages?.length ?? 0})</span>
            <div className="build-stages-meta">
              {buildCounter && <span className="build-queue-counter">{buildCounter}</span>}
              {totalDuration && <span className="build-stages-total">Total {formatDuration(totalDuration)}</span>}
            </div>
          </div>
          {hasStages ? (
            build.stages!.map((stage, index) => (
              <div
                key={index}
                className={`build-stage ${stage.status}`}
                onClick={() => {
                  if (build.buildId) {
                    useStore.getState().setLogViewerBuildId(build.buildId)
                    sendAction('setLogViewCurrentId', { buildId: build.buildId, stage: stage.stageId || stage.name })
                    postMessage({ type: 'showBuildLogs' })
                  }
                }}
                title={`View logs for ${stage.displayName || stage.name}`}
              >
                <StageStatusIcon status={stage.status} />
                <span className="stage-name">{stage.displayName || stage.name}</span>
                {(() => {
                  const stageElapsed = stage.status === 'running'
                    ? runningStageElapsed ?? stage.elapsedSeconds
                    : stage.elapsedSeconds
                  if (stageElapsed === undefined || stageElapsed === null) return null
                  if (stage.status === 'pending') return null
                  return (
                    <span className="stage-time">{formatDuration(stageElapsed)}</span>
                  )
                })()}
              </div>
            ))
          ) : (
            <div className="build-stages-empty">No steps recorded</div>
          )}
        </div>
      )}
    </div>
  )
}
