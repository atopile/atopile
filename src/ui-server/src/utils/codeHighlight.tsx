/**
 * Shared utilities for code highlighting and display.
 * Used across ProjectCard, DependencyCard, and other components.
 */

import React from 'react'

/**
 * Simple ato syntax highlighter.
 * Highlights keywords, types (PascalCase), and strings.
 */
export function highlightAtoCode(code: string): React.ReactNode {
  const lines = code.split('\n')
  return lines.map((line, lineIdx) => {
    const parts: React.ReactNode[] = []
    let keyIdx = 0

    const keywords = ['from', 'import', 'module', 'component', 'interface', 'new', 'assert', 'within', 'trait', 'signal', 'pin']
    const typePattern = /\b([A-Z][a-zA-Z0-9_]*)\b/g
    const stringPattern = /"[^"]*"/g

    const tokens: { start: number; end: number; type: 'string' | 'keyword' | 'type'; text: string }[] = []

    let match
    // Find all strings first (highest priority)
    while ((match = stringPattern.exec(line)) !== null) {
      tokens.push({ start: match.index, end: match.index + match[0].length, type: 'string', text: match[0] })
    }

    // Find keywords (not inside strings)
    for (const kw of keywords) {
      const kwPattern = new RegExp(`\\b${kw}\\b`, 'g')
      while ((match = kwPattern.exec(line)) !== null) {
        const inString = tokens.some(t => t.type === 'string' && match!.index >= t.start && match!.index < t.end)
        if (!inString) {
          tokens.push({ start: match.index, end: match.index + match[0].length, type: 'keyword', text: match[0] })
        }
      }
    }

    // Find types (PascalCase, not overlapping with existing tokens)
    while ((match = typePattern.exec(line)) !== null) {
      const overlaps = tokens.some(t =>
        (match!.index >= t.start && match!.index < t.end) ||
        (match!.index + match![0].length > t.start && match!.index + match![0].length <= t.end)
      )
      if (!overlaps) {
        tokens.push({ start: match.index, end: match.index + match[0].length, type: 'type', text: match[0] })
      }
    }

    tokens.sort((a, b) => a.start - b.start)

    let pos = 0
    for (const token of tokens) {
      if (token.start > pos) {
        parts.push(<span key={keyIdx++}>{line.slice(pos, token.start)}</span>)
      }
      const className = token.type === 'keyword' ? 'ato-keyword' : token.type === 'string' ? 'ato-string' : 'ato-type'
      parts.push(<span key={keyIdx++} className={className}>{token.text}</span>)
      pos = token.end
    }
    if (pos < line.length) {
      parts.push(<span key={keyIdx++}>{line.slice(pos)}</span>)
    }

    return (
      <span key={lineIdx}>
        {parts}
        {lineIdx < lines.length - 1 && '\n'}
      </span>
    )
  })
}

/**
 * Generate import statement for a package.
 */
export function generateImportStatement(packageId: string, moduleName: string): string {
  const className = moduleName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('')
  return `from "${packageId}/${moduleName}.ato" import ${className}`
}

/**
 * Generate usage example for a package.
 */
export function generateUsageExample(moduleName: string): string {
  const varName = moduleName.replace(/-/g, '_')
  const className = moduleName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('')
  return `module MyModule:\n    ${varName} = new ${className}`
}
