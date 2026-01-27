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

    const tokens: { start: number; end: number; type: 'string' | 'keyword' | 'type' | 'comment'; text: string }[] = []

    let match
    // Find all strings first (highest priority)
    while ((match = stringPattern.exec(line)) !== null) {
      tokens.push({ start: match.index, end: match.index + match[0].length, type: 'string', text: match[0] })
    }

    const isInString = (index: number) => tokens.some(
      (t) => t.type === 'string' && index >= t.start && index < t.end
    )

    const findCommentStart = () => {
      let hashIndex = line.indexOf('#')
      while (hashIndex !== -1 && isInString(hashIndex)) {
        hashIndex = line.indexOf('#', hashIndex + 1)
      }
      let slashIndex = line.indexOf('//')
      while (slashIndex !== -1 && isInString(slashIndex)) {
        slashIndex = line.indexOf('//', slashIndex + 2)
      }
      if (hashIndex === -1) return slashIndex
      if (slashIndex === -1) return hashIndex
      return Math.min(hashIndex, slashIndex)
    }

    const commentStart = findCommentStart()

    if (commentStart !== -1) {
      // Drop any string tokens that appear after the comment start.
      for (let i = tokens.length - 1; i >= 0; i -= 1) {
        if (tokens[i].start >= commentStart) {
          tokens.splice(i, 1)
        }
      }
      tokens.push({ start: commentStart, end: line.length, type: 'comment', text: line.slice(commentStart) })
    }

    // Find keywords (not inside strings or comments)
    for (const kw of keywords) {
      const kwPattern = new RegExp(`\\b${kw}\\b`, 'g')
      while ((match = kwPattern.exec(line)) !== null) {
        if (commentStart !== -1 && match.index >= commentStart) {
          continue
        }
        const inString = isInString(match.index)
        if (!inString) {
          tokens.push({ start: match.index, end: match.index + match[0].length, type: 'keyword', text: match[0] })
        }
      }
    }

    // Find types (PascalCase, not overlapping with existing tokens)
    while ((match = typePattern.exec(line)) !== null) {
      if (commentStart !== -1 && match.index >= commentStart) {
        continue
      }
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
      const className = token.type === 'keyword'
        ? 'ato-keyword'
        : token.type === 'string'
          ? 'ato-string'
          : token.type === 'comment'
            ? 'ato-comment'
            : 'ato-type'
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
