import { useEffect, useMemo, useState } from 'react'
import { Loader2, Check, AlertCircle, Package, FileCode, Settings, FolderTree } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { rpcClient } from '../shared/rpcClient'
import type { UiMigrationState } from '../../shared/generated-types'
import './MigrateDialog.css'

type StepStatus = 'idle' | 'running' | 'success' | 'error'

interface MigrationStep {
  id: string
  label: string
  description: string
  topic: string
  mandatory: boolean
  order: number
}

interface StepGroup {
  key: string
  label: string
  icon: LucideIcon
  steps: MigrationStep[]
}

// Maps Lucide icon names (from backend) to components
const ICON_MAP: Record<string, LucideIcon> = {
  Package, FileCode, Settings, FolderTree, AlertCircle,
}

interface TopicInfo {
  id: string
  label: string
  icon: string
}

function buildGroups(steps: MigrationStep[], topics: TopicInfo[]): StepGroup[] {
  const byTopic: Record<string, MigrationStep[]> = {}
  for (const step of steps) {
    if (!byTopic[step.topic]) byTopic[step.topic] = []
    byTopic[step.topic].push(step)
  }

  const groups: StepGroup[] = []
  for (const topic of topics) {
    if (byTopic[topic.id] && byTopic[topic.id].length > 0) {
      groups.push({
        key: topic.id,
        label: topic.label,
        icon: ICON_MAP[topic.icon] || Package,
        steps: byTopic[topic.id],
      })
      delete byTopic[topic.id]
    }
  }
  // Any topics not in the backend list (shouldn't happen, but safe)
  for (const [topicId, topicSteps] of Object.entries(byTopic)) {
    if (topicSteps.length > 0) {
      groups.push({
        key: topicId,
        label: topicId,
        icon: Package,
        steps: topicSteps,
      })
    }
  }
  return groups
}

interface MigrateDialogProps {
  migration: UiMigrationState
  actualVersion: string
  onClose: () => void
}

export function MigrateDialog({ migration, actualVersion, onClose }: MigrateDialogProps) {
  const [selectedSteps, setSelectedSteps] = useState<Set<string>>(new Set())
  const stepKey = useMemo(
    () => migration.steps.map((step) => step.id).join('|'),
    [migration.steps],
  )
  const groups = useMemo(
    () => buildGroups(migration.steps, migration.topics),
    [migration.steps, migration.topics],
  )
  const stepStatuses = useMemo<Record<string, StepStatus>>(
    () =>
      Object.fromEntries(
        migration.stepResults.map((result) => [result.stepId, result.status]),
      ) as Record<string, StepStatus>,
    [migration.stepResults],
  )
  const stepErrors = useMemo<Record<string, string>>(
    () =>
      Object.fromEntries(
        migration.stepResults
          .filter((result) => result.error)
          .map((result) => [result.stepId, result.error!]),
      ),
    [migration.stepResults],
  )
  const isMigrating = migration.running
  const allDone = migration.completed
  const hasErrors =
    migration.stepResults.some((result) => result.status === 'error') || Boolean(migration.error)

  useEffect(() => {
    setSelectedSteps(new Set(migration.steps.map((step) => step.id)))
  }, [migration.projectRoot, stepKey])

  const toggleStep = (stepId: string) => {
    if (isMigrating) return
    const step = migration.steps.find(s => s.id === stepId)
    if (step?.mandatory) return
    setSelectedSteps(prev => {
      const next = new Set(prev)
      if (next.has(stepId)) {
        next.delete(stepId)
      } else {
        next.add(stepId)
      }
      return next
    })
  }

  const handleMigrate = () => {
    const selected = migration.steps
      .filter(s => selectedSteps.has(s.id))
      .map(s => s.id)
    if (selected.length === 0) return

    rpcClient?.sendAction('migrateProjectSteps', {
      projectRoot: migration.projectRoot,
      steps: selected,
    })
  }

  // Keyboard: Escape to close when not migrating
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isMigrating) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isMigrating, onClose])

  const renderStepStatus = (stepId: string) => {
    const status = stepStatuses[stepId]
    if (!status || status === 'idle') return null
    if (status === 'running') {
      return (
        <span className="migrate-step-status">
          <Loader2 size={14} className="spin" />
        </span>
      )
    }
    if (status === 'success') {
      return (
        <span className="migrate-step-status success">
          <Check size={14} />
        </span>
      )
    }
    if (status === 'error') {
      return (
        <span
          className="migrate-step-status error"
          title={stepErrors[stepId] || 'Failed'}
        >
          <AlertCircle size={14} />
        </span>
      )
    }
    return null
  }

  const versionDisplay = actualVersion || 'the latest version'

  if (migration.loading) {
    return (
      <div className="migrate-page">
        <div className="migrate-header">
          <h1 className="migrate-title">Migrate Project</h1>
          <p className="migrate-subtitle">Loading migration steps...</p>
        </div>
        <div className="migrate-loading">
          <Loader2 size={24} className="spin" />
        </div>
      </div>
    )
  }

  if (migration.error && migration.steps.length === 0) {
    return (
      <div className="migrate-page">
        <div className="migrate-header">
          <h1 className="migrate-title">Migrate Project</h1>
          <p className="migrate-subtitle">Failed to load migration steps.</p>
        </div>
        <div className="migrate-banner error">
          <AlertCircle size={16} />
          <span>{migration.error}</span>
        </div>
        <div className="migrate-actions">
          <button type="button" className="migrate-btn secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="migrate-page">
      {/* Header */}
      <div className="migrate-header">
        <h1 className="migrate-title">Migrate Project</h1>
        <p className="migrate-subtitle">
          It seems your project is not ready for atopile {versionDisplay} yet 😞
        </p>
        <p className="migrate-subtitle">
          Don't worry, this guide will make sure your project will be mostly automatically migrated to the latest standard!
        </p>
      </div>

      {/* Git warning */}
      {!isMigrating && (
        <div className="migrate-banner warning">
          <AlertCircle size={16} />
          <span>We recommend committing your changes to git before migrating.</span>
        </div>
      )}

      {/* Step Groups */}
      <div className="migrate-groups">
        {groups.map(group => {
          const GroupIcon = group.icon
          const groupSteps = group.steps
          if (groupSteps.length === 0) return null

          return (
            <div key={group.key} className="migrate-group">
              <div className="migrate-group-header">
                <GroupIcon size={14} className="migrate-group-icon" />
                <span className="migrate-group-label">{group.label}</span>
              </div>

              <div className="migrate-group-steps">
                {groupSteps.map(step => (
                  <div key={step.id} className="migrate-step-card">
                    <label
                      className={`migrate-step ${step.mandatory ? 'disabled' : ''}`}
                      onClick={(e) => {
                        if ((e.target as HTMLElement).tagName !== 'INPUT') {
                          e.preventDefault()
                          toggleStep(step.id)
                        }
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedSteps.has(step.id)}
                        onChange={() => toggleStep(step.id)}
                        disabled={step.mandatory || isMigrating}
                      />
                      <div className="migrate-step-content">
                        <div className="migrate-step-title-row">
                          <span className="migrate-step-label">{step.label}</span>
                          {renderStepStatus(step.id)}
                        </div>
                        <span className="migrate-step-description">{step.description}</span>
                      </div>
                    </label>
                    {stepErrors[step.id] && (
                      <div className="migrate-step-error">{stepErrors[step.id]}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Success / Error banner */}
      {allDone && !hasErrors && (
        <div className="migrate-banner success">
          <Check size={16} />
          <span>Migration complete! You can now close this tab and build your project.</span>
        </div>
      )}
      {allDone && hasErrors && (
        <div className="migrate-banner error">
          <AlertCircle size={16} />
          <span>{migration.error || 'Some steps failed. Check the errors above and try again or fix them manually.'}</span>
        </div>
      )}

      {/* Actions */}
      <div className="migrate-actions">
        <button
          type="button"
          className="migrate-btn secondary"
          onClick={onClose}
          disabled={isMigrating && !allDone}
        >
          {allDone ? 'Close' : 'Cancel'}
        </button>
        {!allDone && (
          <button
            type="button"
            className="migrate-btn primary"
            onClick={handleMigrate}
            disabled={isMigrating || selectedSteps.size === 0}
          >
            {isMigrating ? (
              <>
                <Loader2 size={14} className="spin" />
                Migrating...
              </>
            ) : (
              'Run Migration'
            )}
          </button>
        )}
      </div>
    </div>
  )
}
