import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import { Copy, Check, ChevronDown, ChevronRight, Bot, Wrench, AlertCircle, Terminal, CheckCircle, RotateCcw, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { OutputChunk } from '@/logic';
import { PlanModeDisplay } from './PlanModeDisplay';
import { QuestionDisplay } from './QuestionDisplay';

interface PromptInfo {
  run: number;
  prompt: string;
}

interface OutputStreamProps {
  chunks: OutputChunk[];
  prompts?: PromptInfo[];
  initialPrompt?: string;  // For single-run agents without history
  autoScroll?: boolean;
  verbose?: boolean;
  isAgentRunning?: boolean;
  onSendInput?: (input: string) => void;
}

// Merged display item for friendly mode
interface DisplayItem {
  type: 'assistant' | 'tool_use' | 'tool_result' | 'error' | 'system' | 'run_separator' | 'user_prompt';
  text: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  isStreaming?: boolean;
  isError?: boolean;
  sequences: number[];
  timestamp?: string;
  runNumber?: number;
  hasToolResult?: boolean;  // For tool_use items: whether a corresponding result was received
}

// Format timestamp for display
// Note: Claude's raw output doesn't include timestamps, so historical data
// timestamps are set at parse time and aren't meaningful for relative display.
// We show absolute time format instead.
function formatTime(timestamp: string | undefined): string {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
}

// Extract text content from assistant message data
function extractAssistantText(chunk: OutputChunk): string | null {
  if (chunk.type !== 'assistant') return null;

  // First, check if content is directly available (simplified API format)
  if (chunk.content) {
    return chunk.content;
  }

  // Fall back to nested data.message.content format
  if (!chunk.data) return null;
  const data = chunk.data as { message?: { content?: Array<{ type: string; text?: string }> } };
  const message = data.message;
  if (!message?.content) return null;

  const textContent = message.content
    .filter((c) => c.type === 'text')
    .map((c) => c.text || '')
    .join('');

  return textContent || null;
}

// Process chunks into merged display items for friendly mode
function processChunksForDisplay(
  chunks: OutputChunk[],
  prompts?: PromptInfo[],
  initialPrompt?: string
): DisplayItem[] {
  const items: DisplayItem[] = [];
  let currentStreaming: DisplayItem | null = null;
  let isStreaming = false;
  let currentRunNumber: number | undefined = undefined;

  // Create a map of prompts by run number
  const promptsByRun = new Map<number, string>();
  if (prompts) {
    for (const p of prompts) {
      promptsByRun.set(p.run, p.prompt);
    }
  }

  for (const chunk of chunks) {
    // Check for run boundary and insert separator + prompt
    const chunkRunNumber = chunk.run_number;
    if (chunkRunNumber !== undefined && chunkRunNumber !== currentRunNumber) {
      // Close any open streaming first
      if (currentStreaming) {
        currentStreaming.isStreaming = false;
        currentStreaming = null;
        isStreaming = false;
      }

      // Insert separator if this isn't the first run
      if (currentRunNumber !== undefined) {
        items.push({
          type: 'run_separator',
          text: `Run ${chunkRunNumber}`,
          sequences: [],
          runNumber: chunkRunNumber,
        });
      }

      // Insert user prompt for this run
      // Only use initialPrompt as fallback for run 0 if there are no tracked prompts at all
      // (single-run agent that hasn't been resumed). For multi-run agents, config.prompt
      // has been overwritten with the latest prompt, so it's not valid for run 0.
      const hasTrackedPrompts = promptsByRun.size > 0;
      const runPrompt = promptsByRun.get(chunkRunNumber) ||
        (chunkRunNumber === 0 && !hasTrackedPrompts ? initialPrompt : undefined);
      if (runPrompt) {
        items.push({
          type: 'user_prompt',
          text: runPrompt,
          sequences: [],
          runNumber: chunkRunNumber,
        });
      }

      currentRunNumber = chunkRunNumber;
    } else if (currentRunNumber === undefined && items.length === 0) {
      // First chunk, no run_number - show initial prompt only if no tracked prompts
      // (for single-run agents that haven't been resumed)
      if (initialPrompt && promptsByRun.size === 0) {
        items.push({
          type: 'user_prompt',
          text: initialPrompt,
          sequences: [],
          runNumber: 0,
        });
      }
      currentRunNumber = chunk.run_number ?? 0;
    }

    // Handle streaming start
    if (chunk.type === 'stream_start') {
      isStreaming = true;
      currentStreaming = {
        type: 'assistant',
        text: '',
        isStreaming: true,
        sequences: [chunk.sequence],
        timestamp: chunk.timestamp,
        runNumber: chunkRunNumber,
      };
      items.push(currentStreaming);
      continue;
    }

    // Handle streaming text deltas
    if (chunk.type === 'text_delta') {
      if (currentStreaming) {
        currentStreaming.text += chunk.content || '';
        currentStreaming.sequences.push(chunk.sequence);
      } else {
        currentStreaming = {
          type: 'assistant',
          text: chunk.content || '',
          isStreaming: true,
          sequences: [chunk.sequence],
          timestamp: chunk.timestamp,
          runNumber: chunkRunNumber,
        };
        items.push(currentStreaming);
      }
      continue;
    }

    // Handle streaming stop
    if (chunk.type === 'stream_stop') {
      if (currentStreaming) {
        currentStreaming.isStreaming = false;
        currentStreaming.sequences.push(chunk.sequence);
      }
      isStreaming = false;
      currentStreaming = null;
      continue;
    }

    // Handle complete assistant message (replaces streamed content)
    if (chunk.type === 'assistant') {
      const text = extractAssistantText(chunk);
      if (!text) continue;

      if (currentStreaming && currentStreaming.text) {
        currentStreaming.text = text;
        currentStreaming.isStreaming = false;
        currentStreaming.sequences.push(chunk.sequence);
        currentStreaming = null;
        isStreaming = false;
      } else if (!isStreaming) {
        items.push({
          type: 'assistant',
          text,
          isStreaming: false,
          sequences: [chunk.sequence],
          timestamp: chunk.timestamp,
          runNumber: chunkRunNumber,
        });
      }
      continue;
    }

    // Non-streaming chunk - close any open streaming
    if (currentStreaming) {
      currentStreaming.isStreaming = false;
      currentStreaming = null;
      isStreaming = false;
    }

    if (chunk.type === 'tool_use') {
      // Check if there's a corresponding tool_result after this in the chunks
      // We look for the next tool_result that follows this tool_use
      const toolUseIndex = chunks.indexOf(chunk);
      let hasToolResult = false;
      for (let j = toolUseIndex + 1; j < chunks.length; j++) {
        if (chunks[j].type === 'tool_result') {
          hasToolResult = true;
          break;
        }
        // Stop if we hit another tool_use (means this one doesn't have a result yet)
        if (chunks[j].type === 'tool_use') {
          break;
        }
      }

      items.push({
        type: 'tool_use',
        text: chunk.tool_name || 'tool',
        toolName: chunk.tool_name || undefined,
        toolInput: chunk.tool_input || undefined,
        sequences: [chunk.sequence],
        timestamp: chunk.timestamp,
        runNumber: chunkRunNumber,
        hasToolResult,
      });
    } else if (chunk.type === 'tool_result') {
      items.push({
        type: 'tool_result',
        text: typeof chunk.tool_result === 'string' ? chunk.tool_result : JSON.stringify(chunk.tool_result, null, 2),
        isError: chunk.is_error || false,
        sequences: [chunk.sequence],
        timestamp: chunk.timestamp,
        runNumber: chunkRunNumber,
      });
    } else if (chunk.type === 'error') {
      items.push({
        type: 'error',
        text: chunk.content || 'Unknown error',
        sequences: [chunk.sequence],
        timestamp: chunk.timestamp,
        runNumber: chunkRunNumber,
      });
    }
  }

  return items;
}

// Typing indicator component
function TypingIndicator() {
  return (
    <span className="inline-flex items-center gap-1 ml-1">
      <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </span>
  );
}

// Timestamp display component
function Timestamp({ time }: { time: string | undefined }) {
  const formatted = formatTime(time);
  if (!formatted) return null;
  return (
    <span className="text-[10px] text-gray-600 font-mono">{formatted}</span>
  );
}

// JSON Tree component for pretty verbose display
function JsonTree({ data, depth = 0 }: { data: unknown; depth?: number }) {
  const [collapsed, setCollapsed] = useState(depth > 1);

  if (data === null) return <span className="text-gray-500">null</span>;
  if (data === undefined) return <span className="text-gray-500">undefined</span>;
  if (typeof data === 'boolean') return <span className="text-yellow-400">{data.toString()}</span>;
  if (typeof data === 'number') return <span className="text-blue-400">{data}</span>;
  if (typeof data === 'string') {
    // Truncate long strings
    const maxLen = 100;
    const display = data.length > maxLen ? data.slice(0, maxLen) + '...' : data;
    return <span className="text-green-400">"{display}"</span>;
  }

  if (Array.isArray(data)) {
    if (data.length === 0) return <span className="text-gray-400">[]</span>;
    return (
      <span>
        <button onClick={() => setCollapsed(!collapsed)} className="text-gray-500 hover:text-gray-300">
          {collapsed ? '▶' : '▼'}
        </button>
        <span className="text-gray-400">[</span>
        {collapsed ? (
          <span className="text-gray-500 ml-1">{data.length} items</span>
        ) : (
          <div className="ml-4">
            {data.map((item, i) => (
              <div key={i}>
                <JsonTree data={item} depth={depth + 1} />
                {i < data.length - 1 && <span className="text-gray-500">,</span>}
              </div>
            ))}
          </div>
        )}
        <span className="text-gray-400">]</span>
      </span>
    );
  }

  if (typeof data === 'object') {
    const entries = Object.entries(data);
    if (entries.length === 0) return <span className="text-gray-400">{'{}'}</span>;
    return (
      <span>
        <button onClick={() => setCollapsed(!collapsed)} className="text-gray-500 hover:text-gray-300">
          {collapsed ? '▶' : '▼'}
        </button>
        <span className="text-gray-400">{'{'}</span>
        {collapsed ? (
          <span className="text-gray-500 ml-1">{entries.length} keys</span>
        ) : (
          <div className="ml-4">
            {entries.map(([key, value], i) => (
              <div key={key}>
                <span className="text-purple-400">"{key}"</span>
                <span className="text-gray-400">: </span>
                <JsonTree data={value} depth={depth + 1} />
                {i < entries.length - 1 && <span className="text-gray-500">,</span>}
              </div>
            ))}
          </div>
        )}
        <span className="text-gray-400">{'}'}</span>
      </span>
    );
  }

  return <span className="text-gray-400">{String(data)}</span>;
}

// Run separator component
function RunSeparator({ runNumber }: { runNumber: number }) {
  return (
    <div className="flex items-center gap-3 py-4 my-2">
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
      <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-full">
        <RotateCcw className="w-3.5 h-3.5 text-blue-400" />
        <span className="text-xs font-medium text-blue-400">Resumed • Run {runNumber}</span>
      </div>
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
    </div>
  );
}

// Collapsible wrapper component
function CollapsibleMessage({
  children,
  icon,
  iconBg,
  label,
  labelColor = 'text-gray-500',
  timestamp,
  preview,
  defaultCollapsed = false,
}: {
  children: React.ReactNode;
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  labelColor?: string;
  timestamp?: string;
  preview?: string;
  defaultCollapsed?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <div className="flex gap-3 py-2">
      <div className={`flex-shrink-0 w-8 h-8 ${iconBg} rounded-full flex items-center justify-center`}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div
          className="flex items-center gap-2 mb-1 cursor-pointer select-none"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="w-3 h-3 text-gray-500" />
          ) : (
            <ChevronDown className="w-3 h-3 text-gray-500" />
          )}
          <span className={`text-xs ${labelColor}`}>{label}</span>
          <Timestamp time={timestamp} />
          {collapsed && preview && (
            <span className="text-xs text-gray-500 truncate max-w-[300px]">{preview}</span>
          )}
        </div>
        {!collapsed && children}
      </div>
    </div>
  );
}

// Friendly display item component
interface FriendlyDisplayItemProps {
  item: DisplayItem;
  isAgentRunning?: boolean;
  onSendInput?: (input: string) => void;
  hasToolResult?: boolean;  // Whether this tool_use has a corresponding result
}

function FriendlyDisplayItem({ item, isAgentRunning, onSendInput, hasToolResult }: FriendlyDisplayItemProps) {
  const [expanded, setExpanded] = useState(false);

  if (item.type === 'run_separator') {
    return <RunSeparator runNumber={item.runNumber ?? 0} />;
  }

  if (item.type === 'user_prompt') {
    return (
      <CollapsibleMessage
        icon={<User className="w-4 h-4 text-purple-400" />}
        iconBg="bg-purple-600/20"
        label="You"
        labelColor="text-purple-400"
        preview={item.text.slice(0, 60) + (item.text.length > 60 ? '...' : '')}
      >
        <p className="text-sm text-gray-200 whitespace-pre-wrap">{item.text}</p>
      </CollapsibleMessage>
    );
  }

  if (item.type === 'assistant') {
    const isLong = item.text.length > 500;
    const displayText = isLong && !expanded ? item.text.slice(0, 500) + '...' : item.text;

    return (
      <CollapsibleMessage
        icon={<Bot className="w-4 h-4 text-green-400" />}
        iconBg="bg-green-600/20"
        label="Assistant"
        timestamp={item.timestamp}
        preview={item.text.slice(0, 60) + (item.text.length > 60 ? '...' : '')}
      >
        <div className="text-sm text-gray-200 prose prose-sm prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-pre:my-2 prose-code:text-blue-300 prose-code:bg-gray-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-800 prose-pre:border prose-pre:border-gray-700">
          <ReactMarkdown>{displayText}</ReactMarkdown>
          {item.isStreaming && <TypingIndicator />}
        </div>
        {isLong && (
          <button
            className="text-xs text-blue-400 hover:text-blue-300 mt-1"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          >
            {expanded ? 'Show less' : `Show all (${item.text.length} chars)`}
          </button>
        )}
      </CollapsibleMessage>
    );
  }

  if (item.type === 'tool_use') {
    // Special display for ExitPlanMode tool
    if (item.toolName === 'ExitPlanMode' && item.toolInput) {
      return (
        <PlanModeDisplay
          toolInput={item.toolInput as { allowedPrompts?: Array<{ tool: string; prompt: string }>; plan?: string }}
          timestamp={formatTime(item.timestamp)}
        />
      );
    }

    // Special display for AskUserQuestion tool
    if (item.toolName === 'AskUserQuestion' && item.toolInput) {
      return (
        <QuestionDisplay
          toolInput={item.toolInput as { questions: Array<{ question: string; header?: string; options: Array<{ label: string; description?: string }>; multiSelect?: boolean }>; answers?: Record<string, string>; metadata?: { source?: string } }}
          timestamp={formatTime(item.timestamp)}
          onSendResponse={onSendInput}
          isAgentRunning={isAgentRunning}
          responded={hasToolResult}  // If there's a tool_result, the question was already answered
        />
      );
    }

    // Default tool display
    return (
      <div className="py-1 pl-11">
        <div
          className="flex items-center gap-2 text-xs cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? (
            <ChevronDown className="w-3 h-3 text-gray-500" />
          ) : (
            <ChevronRight className="w-3 h-3 text-gray-500" />
          )}
          <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded-md text-blue-400">
            <Wrench className="w-3 h-3" />
            <span className="font-medium">{item.toolName}</span>
          </div>
          <Timestamp time={item.timestamp} />
        </div>
        {expanded && item.toolInput && (
          <div className="mt-2 ml-5 text-xs bg-gray-800/50 p-2 rounded border border-gray-700/50 overflow-x-auto font-mono">
            <JsonTree data={item.toolInput} />
          </div>
        )}
      </div>
    );
  }

  if (item.type === 'tool_result') {
    const isLong = item.text.length > 200;
    const isSuccess = !item.isError;
    const [showFull, setShowFull] = useState(false);

    return (
      <div className="py-1 pl-11">
        <div
          className={`rounded-md border ${isSuccess ? 'bg-gray-800/30 border-gray-700/50' : 'bg-red-900/20 border-red-800/50'}`}
        >
          <div
            className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer ${isSuccess ? 'border-gray-700/50' : 'border-red-800/50'} ${expanded ? 'border-b' : ''}`}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronDown className="w-3 h-3 text-gray-500" />
            ) : (
              <ChevronRight className="w-3 h-3 text-gray-500" />
            )}
            {isSuccess ? (
              <CheckCircle className="w-3.5 h-3.5 text-green-500" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 text-red-400" />
            )}
            <span className={`text-xs font-medium ${isSuccess ? 'text-gray-400' : 'text-red-400'}`}>
              {isSuccess ? 'Result' : 'Error'}
            </span>
            <Timestamp time={item.timestamp} />
            {!expanded && (
              <span className="text-xs text-gray-500 truncate max-w-[200px]">
                {item.text.slice(0, 50)}{item.text.length > 50 ? '...' : ''}
              </span>
            )}
          </div>
          {expanded && (
            <>
              <pre className={`p-3 text-xs whitespace-pre-wrap break-words overflow-hidden ${isSuccess ? 'text-gray-300' : 'text-red-300'}`}>
                {isLong && !showFull ? item.text.slice(0, 200) + '...' : item.text}
              </pre>
              {isLong && (
                <div className="px-3 pb-2">
                  <button
                    className="text-xs text-blue-400 hover:text-blue-300"
                    onClick={(e) => { e.stopPropagation(); setShowFull(!showFull); }}
                  >
                    {showFull ? 'Show less' : `Show all (${item.text.length} chars)`}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  if (item.type === 'error') {
    return (
      <CollapsibleMessage
        icon={<AlertCircle className="w-4 h-4 text-red-400" />}
        iconBg="bg-red-600/20"
        label="Error"
        labelColor="text-red-400"
        timestamp={item.timestamp}
        preview={item.text.slice(0, 60) + (item.text.length > 60 ? '...' : '')}
      >
        <p className="text-sm text-red-300 whitespace-pre-wrap">{item.text}</p>
      </CollapsibleMessage>
    );
  }

  return null;
}

// Get color classes for chunk type
function getTypeColor(type: string): string {
  switch (type) {
    case 'assistant': return 'text-green-400 bg-green-500/10 border-green-500/30';
    case 'tool_use': return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
    case 'tool_result': return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
    case 'system': return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
    case 'error': return 'text-red-400 bg-red-500/10 border-red-500/30';
    case 'result': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    case 'stream_start':
    case 'stream_stop':
    case 'text_delta': return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
    default: return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
  }
}

// Verbose chunk view with pretty formatting
function VerboseChunkView({ chunk }: { chunk: OutputChunk }) {
  const [expanded, setExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const copyContent = useCallback(() => {
    const content = chunk.data ? JSON.stringify(chunk.data, null, 2) : chunk.content || '';
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [chunk]);

  const typeColor = getTypeColor(chunk.type);

  // Skip stream events in verbose mode (too noisy)
  if (chunk.type === 'stream_start' || chunk.type === 'stream_stop' || chunk.type === 'text_delta') {
    return null;
  }

  return (
    <div className="border border-gray-700/50 rounded-lg mb-2 overflow-hidden bg-gray-900/30">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800/50 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <button
            className="p-0.5 hover:bg-gray-700 rounded"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
          </button>
          <span className={`text-xs font-medium px-2 py-0.5 rounded border ${typeColor}`}>
            {chunk.type}
          </span>
          {chunk.tool_name && (
            <span className="text-xs text-blue-400 font-mono">{chunk.tool_name}</span>
          )}
          <span className="text-xs text-gray-600 font-mono">#{chunk.sequence}</span>
          <Timestamp time={chunk.timestamp} />
        </div>
        <button
          className="p-1 hover:bg-gray-700 rounded transition-colors"
          onClick={copyContent}
          title="Copy JSON"
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-green-400" />
          ) : (
            <Copy className="w-3.5 h-3.5 text-gray-500" />
          )}
        </button>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-3 text-xs font-mono overflow-x-auto">
          {chunk.content && (
            <div className="mb-2">
              <span className="text-gray-500">content: </span>
              <span className="text-green-400 whitespace-pre-wrap">{chunk.content}</span>
            </div>
          )}
          {chunk.tool_input && (
            <div className="mb-2">
              <span className="text-gray-500">tool_input: </span>
              <JsonTree data={chunk.tool_input} />
            </div>
          )}
          {chunk.tool_result && (
            <div className="mb-2">
              <span className="text-gray-500">tool_result: </span>
              {typeof chunk.tool_result === 'string' ? (
                <span className="text-green-400 whitespace-pre-wrap">{chunk.tool_result.slice(0, 500)}{chunk.tool_result.length > 500 ? '...' : ''}</span>
              ) : (
                <JsonTree data={chunk.tool_result} />
              )}
            </div>
          )}
          {chunk.data && !chunk.content && !chunk.tool_input && !chunk.tool_result && (
            <JsonTree data={chunk.data} />
          )}
        </div>
      )}
    </div>
  );
}

export function OutputStream({ chunks, prompts, initialPrompt, autoScroll = true, verbose = false, isAgentRunning, onSendInput }: OutputStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [userScrolled, setUserScrolled] = useState(false);

  // Process chunks for friendly display
  const displayItems = useMemo(() => {
    if (verbose) return null;
    return processChunksForDisplay(chunks, prompts, initialPrompt);
  }, [chunks, prompts, initialPrompt, verbose]);

  // Process chunks with run separators for verbose mode
  const verboseItemsWithSeparators = useMemo(() => {
    if (!verbose) return null;

    const items: Array<{ type: 'chunk' | 'separator'; chunk?: OutputChunk; runNumber?: number }> = [];
    let currentRunNumber: number | undefined = undefined;

    for (const chunk of chunks) {
      const chunkRunNumber = chunk.run_number;
      if (chunkRunNumber !== undefined && chunkRunNumber !== currentRunNumber) {
        // Insert separator when run changes (but not for the first run)
        if (currentRunNumber !== undefined) {
          items.push({ type: 'separator', runNumber: chunkRunNumber });
        }
        currentRunNumber = chunkRunNumber;
      }
      items.push({ type: 'chunk', chunk });
    }

    return items;
  }, [chunks, verbose]);

  // Auto-scroll when new chunks arrive or on initial mount
  useEffect(() => {
    if (autoScroll && !userScrolled && containerRef.current) {
      // Use requestAnimationFrame to ensure DOM has updated
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
      });
    }
  }, [chunks, autoScroll, userScrolled]);

  // Always scroll to bottom on initial mount
  useEffect(() => {
    if (containerRef.current && chunks.length > 0) {
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
      });
    }
    // Only run once when chunks first become available
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chunks.length > 0]);

  // Track user scroll
  const handleScroll = () => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 50;

    setUserScrolled(!isAtBottom);
  };

  if (chunks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-3">
        <Terminal className="w-8 h-8 opacity-50" />
        <p>Waiting for output...</p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`output-stream h-full overflow-y-auto p-4 ${verbose ? 'space-y-0' : 'space-y-0'}`}
      onScroll={handleScroll}
    >
      {verbose ? (
        // Verbose mode - show all chunks with pretty formatting and run separators
        verboseItemsWithSeparators?.map((item, index) => (
          item.type === 'separator' ? (
            <RunSeparator key={`sep-${item.runNumber}-${index}`} runNumber={item.runNumber ?? 0} />
          ) : item.chunk ? (
            <VerboseChunkView key={`${item.chunk.sequence}-${item.chunk.run_number ?? 0}-${index}`} chunk={item.chunk} />
          ) : null
        ))
      ) : (
        // Friendly mode - show merged display items
        displayItems?.map((item, index) => (
          <FriendlyDisplayItem
            key={`${item.sequences.join('-')}-${index}`}
            item={item}
            isAgentRunning={isAgentRunning}
            onSendInput={onSendInput}
            hasToolResult={item.hasToolResult}
          />
        ))
      )}
    </div>
  );
}

export default OutputStream;
