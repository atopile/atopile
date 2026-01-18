import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import { Copy, Check, ChevronDown, ChevronRight, Bot, Wrench, AlertCircle, Terminal, CheckCircle } from 'lucide-react';
import type { OutputChunk } from '@/api/types';

interface OutputStreamProps {
  chunks: OutputChunk[];
  autoScroll?: boolean;
  verbose?: boolean;
}

// Merged display item for friendly mode
interface DisplayItem {
  type: 'assistant' | 'tool_use' | 'tool_result' | 'error' | 'system';
  text: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  isStreaming?: boolean;
  isError?: boolean;
  sequences: number[];
  timestamp?: string;
}

// Format timestamp for display
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
function processChunksForDisplay(chunks: OutputChunk[]): DisplayItem[] {
  const items: DisplayItem[] = [];
  let currentStreaming: DisplayItem | null = null;
  let isStreaming = false;

  for (const chunk of chunks) {
    // Handle streaming start
    if (chunk.type === 'stream_start') {
      isStreaming = true;
      currentStreaming = {
        type: 'assistant',
        text: '',
        isStreaming: true,
        sequences: [chunk.sequence],
        timestamp: chunk.timestamp,
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
      items.push({
        type: 'tool_use',
        text: chunk.tool_name || 'tool',
        toolName: chunk.tool_name || undefined,
        toolInput: chunk.tool_input || undefined,
        sequences: [chunk.sequence],
        timestamp: chunk.timestamp,
      });
    } else if (chunk.type === 'tool_result') {
      items.push({
        type: 'tool_result',
        text: typeof chunk.tool_result === 'string' ? chunk.tool_result : JSON.stringify(chunk.tool_result, null, 2),
        isError: chunk.is_error || false,
        sequences: [chunk.sequence],
        timestamp: chunk.timestamp,
      });
    } else if (chunk.type === 'error') {
      items.push({
        type: 'error',
        text: chunk.content || 'Unknown error',
        sequences: [chunk.sequence],
        timestamp: chunk.timestamp,
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

// Friendly display item component
function FriendlyDisplayItem({ item }: { item: DisplayItem }) {
  const [expanded, setExpanded] = useState(false);

  if (item.type === 'assistant') {
    return (
      <div className="flex gap-3 py-3">
        <div className="flex-shrink-0 w-8 h-8 bg-green-600/20 rounded-full flex items-center justify-center">
          <Bot className="w-4 h-4 text-green-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500">Assistant</span>
            <Timestamp time={item.timestamp} />
          </div>
          <p className="text-sm text-gray-200 whitespace-pre-wrap">
            {item.text}
            {item.isStreaming && <TypingIndicator />}
          </p>
        </div>
      </div>
    );
  }

  if (item.type === 'tool_use') {
    return (
      <div className="py-2 pl-11">
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded-md text-blue-400">
            <Wrench className="w-3 h-3" />
            <span className="font-medium">{item.toolName}</span>
          </div>
          <Timestamp time={item.timestamp} />
          {item.toolInput && (
            <button
              className="text-gray-500 hover:text-gray-400 text-xs"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? 'hide args' : 'show args'}
            </button>
          )}
        </div>
        {expanded && item.toolInput && (
          <div className="mt-2 text-xs bg-gray-800/50 p-2 rounded border border-gray-700/50 overflow-x-auto font-mono">
            <JsonTree data={item.toolInput} />
          </div>
        )}
      </div>
    );
  }

  if (item.type === 'tool_result') {
    const isLong = item.text.length > 300;
    const displayText = isLong && !expanded ? item.text.slice(0, 300) + '...' : item.text;
    const isSuccess = !item.isError;

    return (
      <div className="py-2 pl-11">
        <div className={`rounded-md border ${isSuccess ? 'bg-gray-800/30 border-gray-700/50' : 'bg-red-900/20 border-red-800/50'}`}>
          <div className={`flex items-center gap-2 px-3 py-1.5 border-b ${isSuccess ? 'border-gray-700/50' : 'border-red-800/50'}`}>
            {isSuccess ? (
              <CheckCircle className="w-3.5 h-3.5 text-green-500" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 text-red-400" />
            )}
            <span className={`text-xs font-medium ${isSuccess ? 'text-gray-400' : 'text-red-400'}`}>
              {isSuccess ? 'Result' : 'Error'}
            </span>
            <Timestamp time={item.timestamp} />
          </div>
          <pre className={`p-3 text-xs whitespace-pre-wrap break-words overflow-hidden ${isSuccess ? 'text-gray-300' : 'text-red-300'}`}>
            {displayText}
          </pre>
          {isLong && (
            <div className="px-3 pb-2">
              <button
                className="text-xs text-blue-400 hover:text-blue-300"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? 'Show less' : `Show all (${item.text.length} chars)`}
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (item.type === 'error') {
    return (
      <div className="flex gap-3 py-2">
        <div className="flex-shrink-0 w-8 h-8 bg-red-600/20 rounded-full flex items-center justify-center">
          <AlertCircle className="w-4 h-4 text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-red-400">Error</span>
            <Timestamp time={item.timestamp} />
          </div>
          <p className="text-sm text-red-300 whitespace-pre-wrap">{item.text}</p>
        </div>
      </div>
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

export function OutputStream({ chunks, autoScroll = true, verbose = false }: OutputStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [userScrolled, setUserScrolled] = useState(false);

  // Process chunks for friendly display
  const displayItems = useMemo(() => {
    if (verbose) return null;
    return processChunksForDisplay(chunks);
  }, [chunks, verbose]);

  // Auto-scroll when new chunks arrive
  useEffect(() => {
    if (autoScroll && !userScrolled && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [chunks, autoScroll, userScrolled]);

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
        // Verbose mode - show all chunks with pretty formatting
        chunks.map((chunk, index) => (
          <VerboseChunkView key={`${chunk.sequence}-${index}`} chunk={chunk} />
        ))
      ) : (
        // Friendly mode - show merged display items
        displayItems?.map((item, index) => (
          <FriendlyDisplayItem key={`${item.sequences.join('-')}-${index}`} item={item} />
        ))
      )}
    </div>
  );
}

export default OutputStream;
