/**
 * Performance monitoring utilities for UI snappiness tracking.
 *
 * Modern UI performance standards (RAIL model):
 * - Response: < 100ms for user interactions
 * - Animation: < 16ms per frame (60fps)
 * - Idle: maximize idle time
 * - Load: < 1000ms for meaningful content
 *
 * Web Vitals targets:
 * - First Input Delay (FID): < 100ms
 * - Interaction to Next Paint (INP): < 200ms
 * - Cumulative Layout Shift (CLS): < 0.1
 */

interface PerfStats {
  count: number
  total: number
  min: number
  max: number
  avg: number
  p50: number
  p95: number
  p99: number
  recent: number[]
}

// Store for tracking metrics over time
const metricsStore = new Map<string, number[]>()
const MAX_SAMPLES = 100

// Performance thresholds (in ms)
const THRESHOLDS = {
  fast: 16,      // Single frame budget (60fps)
  good: 50,      // Feels instant
  acceptable: 100, // Still responsive
  slow: 200,     // Noticeable delay
  critical: 500, // User frustration
}

// Color codes for console output
const COLORS = {
  fast: '\x1b[32m',      // Green
  good: '\x1b[36m',      // Cyan
  acceptable: '\x1b[33m', // Yellow
  slow: '\x1b[35m',      // Magenta
  critical: '\x1b[31m',   // Red
  reset: '\x1b[0m',
  dim: '\x1b[2m',
  bold: '\x1b[1m',
}

function getColor(duration: number): string {
  if (duration < THRESHOLDS.fast) return COLORS.fast
  if (duration < THRESHOLDS.good) return COLORS.good
  if (duration < THRESHOLDS.acceptable) return COLORS.acceptable
  if (duration < THRESHOLDS.slow) return COLORS.slow
  return COLORS.critical
}

function getRating(duration: number): string {
  if (duration < THRESHOLDS.fast) return 'FAST'
  if (duration < THRESHOLDS.good) return 'GOOD'
  if (duration < THRESHOLDS.acceptable) return 'OK'
  if (duration < THRESHOLDS.slow) return 'SLOW'
  return 'CRITICAL'
}

function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}µs`
  if (ms < 1000) return `${ms.toFixed(2)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function calculatePercentile(sorted: number[], percentile: number): number {
  const index = Math.ceil((percentile / 100) * sorted.length) - 1
  return sorted[Math.max(0, index)]
}

function getStats(name: string): PerfStats | null {
  const samples = metricsStore.get(name)
  if (!samples || samples.length === 0) return null

  const sorted = [...samples].sort((a, b) => a - b)
  const total = samples.reduce((a, b) => a + b, 0)

  return {
    count: samples.length,
    total,
    min: sorted[0],
    max: sorted[sorted.length - 1],
    avg: total / samples.length,
    p50: calculatePercentile(sorted, 50),
    p95: calculatePercentile(sorted, 95),
    p99: calculatePercentile(sorted, 99),
    recent: samples.slice(-5),
  }
}

function recordMetric(name: string, duration: number): void {
  if (!metricsStore.has(name)) {
    metricsStore.set(name, [])
  }
  const samples = metricsStore.get(name)!
  samples.push(duration)
  if (samples.length > MAX_SAMPLES) {
    samples.shift()
  }
}

/**
 * Log a performance measurement with visual formatting
 */
export function logPerf(
  name: string,
  duration: number,
  metadata?: Record<string, unknown>
): void {
  recordMetric(name, duration)

  const color = getColor(duration)
  const rating = getRating(duration)
  const formatted = formatDuration(duration)

  const metaStr = metadata
    ? ` ${COLORS.dim}${JSON.stringify(metadata)}${COLORS.reset}`
    : ''

  console.log(
    `${COLORS.dim}[PERF]${COLORS.reset} ` +
    `${color}${COLORS.bold}${rating}${COLORS.reset} ` +
    `${name}: ${color}${formatted}${COLORS.reset}` +
    metaStr
  )

  // UI server is VS Code-agnostic; no VS Code postMessage reporting.
}

/**
 * Measure the execution time of a synchronous function
 */
export function measure<T>(
  name: string,
  fn: () => T,
  metadata?: Record<string, unknown>
): T {
  const start = performance.now()
  try {
    return fn()
  } finally {
    const duration = performance.now() - start
    logPerf(name, duration, metadata)
  }
}

/**
 * Measure the execution time of an async function
 */
export async function measureAsync<T>(
  name: string,
  fn: () => Promise<T>,
  metadata?: Record<string, unknown>
): Promise<T> {
  const start = performance.now()
  try {
    return await fn()
  } finally {
    const duration = performance.now() - start
    logPerf(name, duration, metadata)
  }
}

/**
 * Create a performance marker that can be ended later
 */
export function startMark(name: string): (metadata?: Record<string, unknown>) => void {
  const start = performance.now()
  return (metadata?: Record<string, unknown>) => {
    const duration = performance.now() - start
    logPerf(name, duration, metadata)
  }
}

/**
 * Hook-friendly performance measurement for React effects
 */
export function createPerfTimer(name: string) {
  let start: number | null = null

  return {
    start: () => {
      start = performance.now()
    },
    end: (metadata?: Record<string, unknown>) => {
      if (start !== null) {
        const duration = performance.now() - start
        logPerf(name, duration, metadata)
        start = null
      }
    },
  }
}

/**
 * Log a render/update event (for tracking re-renders)
 */
export function logRender(component: string, reason?: string): void {
  const reasonStr = reason ? ` (${reason})` : ''
  console.log(
    `${COLORS.dim}[RENDER]${COLORS.reset} ` +
    `${component}${reasonStr}`
  )
}

/**
 * Log state/message size for bandwidth tracking
 */
export function logDataSize(name: string, data: unknown): void {
  const json = JSON.stringify(data)
  const bytes = new Blob([json]).size
  const formatted = bytes < 1024
    ? `${bytes}B`
    : bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(1)}KB`
      : `${(bytes / (1024 * 1024)).toFixed(2)}MB`

  const color = bytes < 10 * 1024 ? COLORS.fast
    : bytes < 100 * 1024 ? COLORS.good
    : bytes < 500 * 1024 ? COLORS.acceptable
    : COLORS.slow

  console.log(
    `${COLORS.dim}[SIZE]${COLORS.reset} ` +
    `${name}: ${color}${formatted}${COLORS.reset}`
  )

  // Send to dev server
  const api = getVsCodeApi()
  if (api) {
    api.postMessage({ type: 'perf', name: `size:${name}`, duration: bytes / 1024, metadata: { bytes, formatted } })
  }
}

/**
 * Print performance summary for all tracked metrics
 */
export function printPerfSummary(): void {
  console.log('\n' + '='.repeat(60))
  console.log(`${COLORS.bold}PERFORMANCE SUMMARY${COLORS.reset}`)
  console.log('='.repeat(60))

  const entries = Array.from(metricsStore.entries())
    .map(([name, _]) => ({ name, stats: getStats(name)! }))
    .filter(e => e.stats)
    .sort((a, b) => b.stats.avg - a.stats.avg)

  for (const { name, stats } of entries) {
    const avgColor = getColor(stats.avg)
    const p95Color = getColor(stats.p95)

    console.log(
      `\n${COLORS.bold}${name}${COLORS.reset} ` +
      `${COLORS.dim}(${stats.count} samples)${COLORS.reset}`
    )
    console.log(
      `  avg: ${avgColor}${formatDuration(stats.avg)}${COLORS.reset} | ` +
      `p50: ${formatDuration(stats.p50)} | ` +
      `p95: ${p95Color}${formatDuration(stats.p95)}${COLORS.reset} | ` +
      `p99: ${formatDuration(stats.p99)}`
    )
    console.log(
      `  min: ${formatDuration(stats.min)} | ` +
      `max: ${formatDuration(stats.max)}`
    )
  }

  console.log('\n' + '='.repeat(60) + '\n')
}

/**
 * Clear all stored metrics
 */
export function clearMetrics(): void {
  metricsStore.clear()
}

/**
 * Get raw metrics data for external analysis
 */
export function getMetrics(): Map<string, PerfStats> {
  const result = new Map<string, PerfStats>()
  Array.from(metricsStore.keys()).forEach(name => {
    const stats = getStats(name)
    if (stats) result.set(name, stats)
  })
  return result
}

// Expose to window for debugging
if (typeof window !== 'undefined') {
  (window as any).__perf = {
    printSummary: printPerfSummary,
    getMetrics,
    clearMetrics,
    THRESHOLDS,
  }
}
