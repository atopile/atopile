export type BuildStatus = 'idle' | 'building' | 'success' | 'error' | 'warning'

export type BuildStage = 'parsing' | 'compiling' | 'linking' | 'generating' | 'verifying' | 'complete'

export interface Build {
  id: string
  name: string
  entry: string
  status: BuildStatus
  currentStage?: BuildStage
  progress?: number
  errors?: number
  warnings?: number
  duration?: number
  startedAt?: string
  finishedAt?: string
  stages: BuildStageInfo[]
}

export interface BuildStageInfo {
  name: BuildStage
  status: 'pending' | 'running' | 'success' | 'error' | 'warning'
  duration?: number
}

export type LogLevel = 'error' | 'warning' | 'info' | 'debug'

export interface LogEntry {
  id: string
  level: LogLevel
  message: string
  timestamp: string
  source?: string
  line?: number
  column?: number
  details?: string
  buildTarget?: string
  stage?: BuildStage
  raw?: string
}
