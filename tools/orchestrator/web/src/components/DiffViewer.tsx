import { useMemo, useState } from 'react';
import { html, Diff2HtmlConfig } from 'diff2html';
import { ChevronDown, ChevronRight, FileCode, Columns, AlignLeft, Maximize2, X, Plus, Minus, FileEdit } from 'lucide-react';

interface DiffViewerProps {
  diffText: string;
  filePath?: string;
  defaultCollapsed?: boolean;
}

type ViewMode = 'side-by-side' | 'unified';

interface ParsedLine {
  lineNum: number;
  content: string;
  type: 'context' | 'add' | 'delete';
}

// Parse unified diff format
function parseUnifiedDiff(text: string): { filePath: string; lines: ParsedLine[]; additions: number; deletions: number } | null {
  const filePathMatch = text.match(/(?:---|\+\+\+)\s+[ab]\/(.+)/);
  const filePath = filePathMatch?.[1] || 'file';

  const lines: ParsedLine[] = [];
  let additions = 0;
  let deletions = 0;
  let currentLineNum = 1;

  // Find the hunk header to get starting line
  const hunkMatch = text.match(/@@ -(\d+)/);
  if (hunkMatch) {
    currentLineNum = parseInt(hunkMatch[1], 10);
  }

  const diffLines = text.split('\n');
  for (const line of diffLines) {
    // Skip headers
    if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('@@') || line.startsWith('diff ')) {
      continue;
    }

    if (line.startsWith('+')) {
      lines.push({ lineNum: currentLineNum, content: line.slice(1), type: 'add' });
      additions++;
      currentLineNum++;
    } else if (line.startsWith('-')) {
      lines.push({ lineNum: currentLineNum, content: line.slice(1), type: 'delete' });
      deletions++;
    } else if (line.startsWith(' ') || line === '') {
      lines.push({ lineNum: currentLineNum, content: line.slice(1) || '', type: 'context' });
      currentLineNum++;
    }
  }

  if (lines.length === 0) return null;
  return { filePath, lines, additions, deletions };
}

// Parse the "cat -n" format that Edit tool returns
function parseEditToolOutput(text: string): { filePath: string; lines: ParsedLine[]; additions: number; deletions: number } | null {
  const filePathMatch = text.match(/The file ([^\s]+) has been (?:updated|created)/);
  const filePath = filePathMatch?.[1] || 'unknown';

  const snippetMatch = text.match(/on a snippet[^:]*:\n([\s\S]+)$/);
  if (!snippetMatch) return null;

  const snippet = snippetMatch[1];
  const rawLines = snippet.split('\n');
  const lines: ParsedLine[] = [];

  for (const line of rawLines) {
    const match = line.match(/^\s*(\d+)\t(.*)$/);
    if (match) {
      lines.push({
        lineNum: parseInt(match[1], 10),
        content: match[2],
        type: 'context'
      });
    }
  }

  if (lines.length === 0) return null;
  return { filePath, lines, additions: 0, deletions: 0 };
}

// Try to detect if text contains a unified diff format
function isUnifiedDiff(text: string): boolean {
  return text.includes('@@') && (text.includes('---') || text.includes('+++'));
}

// Syntax highlighting for code content
function highlightCode(content: string): React.ReactNode {
  // Simple keyword highlighting
  const keywords = /\b(const|let|var|function|return|if|else|for|while|import|export|from|class|interface|type|extends|implements|new|this|true|false|null|undefined|async|await)\b/g;
  const strings = /(["'`])(?:(?!\1)[^\\]|\\.)*?\1/g;
  const comments = /(\/\/.*$|\/\*[\s\S]*?\*\/)/gm;
  const numbers = /\b(\d+\.?\d*)\b/g;

  let result = content;

  // Replace in specific order to avoid conflicts
  const replacements: { start: number; end: number; replacement: string }[] = [];

  // Find all matches
  let match;

  // Comments (highest priority)
  while ((match = comments.exec(content)) !== null) {
    replacements.push({
      start: match.index,
      end: match.index + match[0].length,
      replacement: `<span class="text-gray-500">${match[0]}</span>`
    });
  }

  // Strings
  while ((match = strings.exec(content)) !== null) {
    if (!replacements.some(r => match!.index >= r.start && match!.index < r.end)) {
      replacements.push({
        start: match.index,
        end: match.index + match[0].length,
        replacement: `<span class="text-amber-300">${match[0]}</span>`
      });
    }
  }

  // Keywords
  while ((match = keywords.exec(content)) !== null) {
    if (!replacements.some(r => match!.index >= r.start && match!.index < r.end)) {
      replacements.push({
        start: match.index,
        end: match.index + match[0].length,
        replacement: `<span class="text-purple-400">${match[0]}</span>`
      });
    }
  }

  // Numbers
  while ((match = numbers.exec(content)) !== null) {
    if (!replacements.some(r => match!.index >= r.start && match!.index < r.end)) {
      replacements.push({
        start: match.index,
        end: match.index + match[0].length,
        replacement: `<span class="text-blue-400">${match[0]}</span>`
      });
    }
  }

  // Sort by position descending and apply replacements
  replacements.sort((a, b) => b.start - a.start);
  for (const r of replacements) {
    result = result.slice(0, r.start) + r.replacement + result.slice(r.end);
  }

  return <span dangerouslySetInnerHTML={{ __html: result }} />;
}

// Pretty inline code preview component
function InlinePreview({
  lines,
  filePath,
  additions,
  deletions,
  onExpand
}: {
  lines: ParsedLine[];
  filePath: string;
  additions: number;
  deletions: number;
  onExpand: () => void;
}) {
  const fileName = filePath.split('/').pop() || filePath;
  const previewLines = lines.slice(0, 12);
  const hasMore = lines.length > 12;
  const startLine = lines[0]?.lineNum || 1;
  const endLine = lines[lines.length - 1]?.lineNum || startLine;

  return (
    <div className="font-mono text-xs">
      {/* File header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded-md">
            <FileEdit className="w-3.5 h-3.5 text-blue-400" />
            <span className="font-medium text-blue-300">{fileName}</span>
          </div>
          <span className="text-gray-500 text-[10px]">
            L{startLine}–{endLine}
          </span>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-2">
          {additions > 0 && (
            <span className="flex items-center gap-1 text-green-400 text-[10px]">
              <Plus className="w-3 h-3" />
              {additions}
            </span>
          )}
          {deletions > 0 && (
            <span className="flex items-center gap-1 text-red-400 text-[10px]">
              <Minus className="w-3 h-3" />
              {deletions}
            </span>
          )}
        </div>
      </div>

      {/* Code block */}
      <div className="bg-gray-950 rounded-lg border border-gray-800 overflow-hidden shadow-lg">
        {previewLines.map((line, idx) => (
          <div
            key={idx}
            className={`flex group transition-colors ${
              line.type === 'add'
                ? 'bg-green-950/40 hover:bg-green-950/60'
                : line.type === 'delete'
                ? 'bg-red-950/40 hover:bg-red-950/60'
                : 'hover:bg-gray-800/50'
            }`}
          >
            {/* Line indicator */}
            <span className={`w-6 flex-shrink-0 flex items-center justify-center text-[10px] ${
              line.type === 'add'
                ? 'text-green-500 bg-green-950/50'
                : line.type === 'delete'
                ? 'text-red-500 bg-red-950/50'
                : 'text-gray-600 bg-gray-900/50'
            }`}>
              {line.type === 'add' ? '+' : line.type === 'delete' ? '−' : ''}
            </span>

            {/* Line number */}
            <span className={`w-10 flex-shrink-0 px-2 py-0.5 text-right select-none border-r ${
              line.type === 'add'
                ? 'text-green-600 bg-green-950/30 border-green-900/50'
                : line.type === 'delete'
                ? 'text-red-600 bg-red-950/30 border-red-900/50'
                : 'text-gray-600 bg-gray-900/30 border-gray-800'
            }`}>
              {line.lineNum}
            </span>

            {/* Code content */}
            <span className={`flex-1 px-3 py-0.5 whitespace-pre overflow-x-auto ${
              line.type === 'add'
                ? 'text-green-300'
                : line.type === 'delete'
                ? 'text-red-300 line-through opacity-70'
                : 'text-gray-300'
            }`}>
              {line.type === 'context' ? highlightCode(line.content) : line.content || ' '}
            </span>
          </div>
        ))}

        {/* More lines indicator */}
        {hasMore && (
          <button
            onClick={onExpand}
            className="w-full px-3 py-2 text-[11px] text-gray-400 bg-gray-900/50 border-t border-gray-800 hover:bg-gray-800/50 hover:text-gray-300 transition-colors flex items-center justify-center gap-2"
          >
            <ChevronDown className="w-3 h-3" />
            {lines.length - 12} more lines
            <span className="text-blue-400">• Click to expand</span>
          </button>
        )}
      </div>
    </div>
  );
}

// Full diff panel (modal-like overlay)
function FullDiffPanel({
  diffHtml,
  filePath,
  viewMode,
  setViewMode,
  onClose,
  additions,
  deletions
}: {
  diffHtml: string;
  filePath: string;
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  onClose: () => void;
  additions: number;
  deletions: number;
}) {
  const fileName = filePath.split('/').pop() || filePath;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <div
        className="diff-viewer w-full max-w-6xl h-full sm:h-auto sm:max-h-[90vh] flex flex-col rounded-xl border border-gray-700 bg-gray-900 shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header - responsive layout */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between px-3 sm:px-4 py-2 sm:py-3 bg-gradient-to-r from-gray-800 to-gray-850 border-b border-gray-700 gap-2 sm:gap-0">
          {/* File info */}
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <div className="p-1.5 sm:p-2 bg-blue-500/20 rounded-lg flex-shrink-0">
              <FileCode className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-sm sm:text-base font-semibold text-gray-100 truncate block">{fileName}</span>
              <div className="flex items-center gap-2 sm:gap-3 mt-0.5">
                <span className="text-[10px] sm:text-xs text-gray-500 truncate max-w-[150px] sm:max-w-[300px]" title={filePath}>
                  {filePath}
                </span>
                {(additions > 0 || deletions > 0) && (
                  <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs flex-shrink-0">
                    {additions > 0 && (
                      <span className="flex items-center gap-0.5 text-green-400">
                        <Plus className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                        {additions}
                      </span>
                    )}
                    {deletions > 0 && (
                      <span className="flex items-center gap-0.5 text-red-400">
                        <Minus className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                        {deletions}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between sm:justify-end gap-2 sm:gap-3">
            {/* View mode toggle */}
            <div className="flex items-center bg-gray-800 rounded-lg p-0.5 sm:p-1 border border-gray-700">
              <button
                className={`flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md text-[10px] sm:text-xs font-medium transition-all ${
                  viewMode === 'side-by-side'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
                }`}
                onClick={() => setViewMode('side-by-side')}
              >
                <Columns className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                <span className="hidden xs:inline">Split</span>
              </button>
              <button
                className={`flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md text-[10px] sm:text-xs font-medium transition-all ${
                  viewMode === 'unified'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
                }`}
                onClick={() => setViewMode('unified')}
              >
                <AlignLeft className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                <span className="hidden xs:inline">Unified</span>
              </button>
            </div>

            <button
              className="p-1.5 sm:p-2 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
              onClick={onClose}
              title="Close (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Diff content - full height on mobile */}
        <div
          className="diff-content flex-1 overflow-auto text-xs sm:text-sm bg-gray-950"
          dangerouslySetInnerHTML={{ __html: diffHtml }}
        />
      </div>
    </div>
  );
}

export function DiffViewer({ diffText, filePath, defaultCollapsed = false }: DiffViewerProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [viewMode, setViewMode] = useState<ViewMode>('unified');
  const [showFullPanel, setShowFullPanel] = useState(false);

  const { html: diffHtml, detectedFilePath, parsedLines, additions, deletions } = useMemo(() => {
    let detectedPath = filePath;
    let lines: ParsedLine[] = [];
    let adds = 0;
    let dels = 0;

    // Check if it's already a unified diff
    if (isUnifiedDiff(diffText)) {
      const parsed = parseUnifiedDiff(diffText);
      if (parsed) {
        detectedPath = parsed.filePath;
        lines = parsed.lines;
        adds = parsed.additions;
        dels = parsed.deletions;
      }
    } else {
      // Try to parse Edit tool output format
      const parsed = parseEditToolOutput(diffText);
      if (parsed) {
        detectedPath = parsed.filePath;
        lines = parsed.lines;
        adds = parsed.additions;
        dels = parsed.deletions;
      } else {
        return { html: null, detectedFilePath: null, parsedLines: [], additions: 0, deletions: 0 };
      }
    }

    // Generate diff for the modal view
    const diffLines = [
      `--- a/${detectedPath}`,
      `+++ b/${detectedPath}`,
      `@@ -${lines[0]?.lineNum || 1},${lines.length} +${lines[0]?.lineNum || 1},${lines.length} @@`,
      ...lines.map(l => {
        if (l.type === 'add') return `+${l.content}`;
        if (l.type === 'delete') return `-${l.content}`;
        return ` ${l.content}`;
      })
    ].join('\n');

    const config: Diff2HtmlConfig = {
      drawFileList: false,
      matching: 'lines',
      outputFormat: viewMode === 'side-by-side' ? 'side-by-side' : 'line-by-line',
      renderNothingWhenEmpty: false,
    };

    try {
      const rendered = html(diffLines, config);
      return { html: rendered, detectedFilePath: detectedPath, parsedLines: lines, additions: adds, deletions: dels };
    } catch {
      return { html: null, detectedFilePath: null, parsedLines: [], additions: 0, deletions: 0 };
    }
  }, [diffText, filePath, viewMode]);

  // If we couldn't parse as diff, return null to let parent show raw text
  if (!diffHtml) {
    return null;
  }

  const displayPath = detectedFilePath || filePath || 'file';
  const fileName = displayPath.split('/').pop() || displayPath;

  return (
    <>
      <div className="diff-viewer rounded-xl border border-gray-800 overflow-hidden bg-gray-900/80 shadow-lg">
        {/* Compact header */}
        <div
          className="flex items-center justify-between px-3 py-2 bg-gradient-to-r from-gray-800/80 to-gray-850/80 border-b border-gray-800 cursor-pointer hover:from-gray-800 hover:to-gray-850 transition-colors"
          onClick={() => setCollapsed(!collapsed)}
        >
          <div className="flex items-center gap-2">
            <span className="text-gray-500">
              {collapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </span>
            <FileCode className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-gray-200">{fileName}</span>
            {(additions > 0 || deletions > 0) && (
              <div className="flex items-center gap-1.5 ml-2">
                {additions > 0 && (
                  <span className="text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded">
                    +{additions}
                  </span>
                )}
                {deletions > 0 && (
                  <span className="text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">
                    −{deletions}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Expand button */}
          {!collapsed && (
            <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
              <button
                className="p-1.5 rounded-md text-gray-500 hover:text-gray-200 hover:bg-gray-700 transition-colors"
                onClick={() => setShowFullPanel(true)}
                title="Open in panel"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Inline preview */}
        {!collapsed && (
          <div className="p-3 bg-gray-900/50">
            <InlinePreview
              lines={parsedLines}
              filePath={displayPath}
              additions={additions}
              deletions={deletions}
              onExpand={() => setShowFullPanel(true)}
            />
          </div>
        )}
      </div>

      {/* Full panel modal */}
      {showFullPanel && diffHtml && (
        <FullDiffPanel
          diffHtml={diffHtml}
          filePath={displayPath}
          viewMode={viewMode}
          setViewMode={setViewMode}
          onClose={() => setShowFullPanel(false)}
          additions={additions}
          deletions={deletions}
        />
      )}
    </>
  );
}

export default DiffViewer;
