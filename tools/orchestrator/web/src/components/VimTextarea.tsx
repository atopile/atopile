import { useState, useRef, useCallback, useEffect, KeyboardEvent } from 'react';

type VimMode = 'normal' | 'insert' | 'visual-char' | 'visual-line';
type CompletionMode = 'code' | 'prompt';

interface CompletionConfig {
  enabled: boolean;
  endpoint: string; // e.g., "http://localhost:11434/api/generate" for Ollama
  model: string; // e.g., "deepseek-coder:6.7b", "qwen2.5-coder:7b"
  mode: CompletionMode; // 'code' for single-line, 'prompt' for multi-line natural language
  debounceMs?: number;
  maxTokens?: number;
}

interface VimTextareaProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  vimMode: boolean;
  onVimModeToggle: (enabled: boolean) => void;
  className?: string;
  completion?: CompletionConfig;
}

interface CompletionResponse {
  completion: string;
  confidence?: number;
}

async function fetchOllamaCompletion(
  endpoint: string,
  model: string,
  userText: string,
  maxTokens: number,
  mode: CompletionMode
): Promise<string> {
  try {
    const isPromptMode = mode === 'prompt';

    // Build instruction prompt for tab-completion behavior
    const systemPrompt = isPromptMode
      ? `You are an autocomplete assistant for writing prompts to AI agents. Your task is to predict and complete the user's current thought.

Rules:
- Output ONLY the completion text that continues from where the user stopped
- Do NOT repeat any text the user already wrote
- Keep completions concise (1-2 sentences max)
- Match the user's writing style and tone
- If the text looks complete, return empty completion
- Focus on natural, helpful continuations for AI prompts`
      : `You are a code autocomplete assistant. Complete the code naturally.

Rules:
- Output ONLY the completion, not the existing code
- Keep completions short (usually one line)
- Match the coding style
- If the code looks complete, return empty completion`;

    const userPrompt = `Complete this text (respond with JSON):

TEXT TO COMPLETE:
${userText}

Respond with JSON: {"completion": "<your completion here>", "confidence": <0.0-1.0>}
If no completion needed, respond: {"completion": "", "confidence": 1.0}`;

    // Use chat endpoint for better instruction following
    const chatEndpoint = endpoint.replace('/api/generate', '/api/chat');

    const body = {
      model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      stream: false,
      format: 'json',
      options: {
        num_predict: maxTokens,
        temperature: isPromptMode ? 0.3 : 0.1,
      },
    };

    const response = await fetch(chatEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Ollama response error:', response.status, errorText);
      throw new Error(`Ollama error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    const content = data.message?.content || '';

    // Parse JSON response
    try {
      const parsed: CompletionResponse = JSON.parse(content);
      console.log('Completion response:', parsed);
      return parsed.completion || '';
    } catch {
      // Fallback: try to extract completion from non-JSON response
      console.warn('Failed to parse JSON, using raw response:', content);
      return content.trim();
    }
  } catch (error) {
    console.error('Completion error:', error);
    throw error;
  }
}

// For FIM (fill-in-middle) models like CodeLlama, DeepSeek
async function fetchFIMCompletion(
  endpoint: string,
  model: string,
  prefix: string,
  suffix: string,
  maxTokens: number,
  mode: CompletionMode
): Promise<string> {
  try {
    // DeepSeek/CodeLlama FIM format
    const prompt = `<|fim▁begin|>${prefix}<|fim▁hole|>${suffix}<|fim▁end|>`;
    const isPromptMode = mode === 'prompt';

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model,
        prompt,
        stream: false,
        raw: true,
        options: {
          num_predict: maxTokens,
          temperature: isPromptMode ? 0.4 : 0.2,
          stop: isPromptMode
            ? ['<|fim', '\n\n\n']
            : ['<|fim', '\n\n'],
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`Ollama error: ${response.status}`);
    }

    const data = await response.json();
    return data.response || '';
  } catch (error) {
    console.error('FIM completion error:', error);
    return '';
  }
}

export function VimTextarea({
  value,
  onChange,
  onSubmit,
  placeholder,
  disabled,
  vimMode,
  onVimModeToggle,
  className = '',
  completion,
}: VimTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<VimMode>('normal');
  const [cursorPos, setCursorPos] = useState(0);
  const [yankBuffer, setYankBuffer] = useState('');
  const [yankType, setYankType] = useState<'char' | 'line'>('char');
  const [pendingCommand, setPendingCommand] = useState('');
  const [visualStart, setVisualStart] = useState(0);

  // Local state for snappy input - syncs to parent debounced
  const [localValue, setLocalValue] = useState(value);
  const localValueRef = useRef(value);
  const syncTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Completion state
  const [suggestion, setSuggestion] = useState('');
  const [isLoadingSuggestion, setIsLoadingSuggestion] = useState(false);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const completionAbortRef = useRef<AbortController | null>(null);

  // Sync local value to parent (debounced for performance)
  const syncToParent = useCallback((newValue: string) => {
    localValueRef.current = newValue;
    setLocalValue(newValue);

    // Clear existing timeout
    if (syncTimeoutRef.current) {
      clearTimeout(syncTimeoutRef.current);
    }

    // Debounce sync to parent - keeps typing snappy
    syncTimeoutRef.current = setTimeout(() => {
      onChange(newValue);
    }, 16); // ~1 frame, feels instant but batches updates
  }, [onChange]);

  // Sync from parent when value prop changes externally
  useEffect(() => {
    if (value !== localValueRef.current) {
      localValueRef.current = value;
      setLocalValue(value);
    }
  }, [value]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current);
      }
    };
  }, []);

  // Reset to normal mode when vim mode is enabled
  useEffect(() => {
    if (vimMode) {
      setMode('normal');
    }
  }, [vimMode]);

  // Clear suggestion when value changes
  useEffect(() => {
    setSuggestion('');
  }, [localValue]);

  // Debounced completion fetching
  useEffect(() => {
    // In vim mode, only complete in insert mode
    // In non-vim mode, always allow completion
    const canComplete = !vimMode || mode === 'insert';

    if (!completion?.enabled || !localValue || !canComplete) {
      setSuggestion('');
      return;
    }

    // Only suggest at end of text or end of line
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPosition = textarea.selectionStart;
    const textAfterCursor = localValue.slice(cursorPosition);
    const isAtEndOrLineEnd = !textAfterCursor || textAfterCursor.startsWith('\n');

    if (!isAtEndOrLineEnd) {
      setSuggestion('');
      return;
    }

    const debounceMs = completion.debounceMs ?? 500;
    const completionMode = completion.mode ?? 'code';
    // More tokens for prompt mode since we want multi-line suggestions
    const maxTokens = completion.maxTokens ?? (completionMode === 'prompt' ? 150 : 50);

    const timer = setTimeout(async () => {
      // Cancel any pending request
      if (completionAbortRef.current) {
        completionAbortRef.current.abort();
      }
      completionAbortRef.current = new AbortController();

      setIsLoadingSuggestion(true);
      setCompletionError(null);

      const prefix = localValue.slice(0, cursorPosition);
      const suffix = localValue.slice(cursorPosition);

      let result = '';

      try {
        // Use FIM for supported models (only in code mode), otherwise regular completion
        const isFIMModel = completion.model.includes('deepseek') ||
                           completion.model.includes('codellama') ||
                           completion.model.includes('starcoder');

        // FIM is mainly for code, use regular completion for prompt mode
        if (isFIMModel && suffix && completionMode === 'code') {
          result = await fetchFIMCompletion(
            completion.endpoint,
            completion.model,
            prefix,
            suffix,
            maxTokens,
            completionMode
          );
        } else {
          result = await fetchOllamaCompletion(
            completion.endpoint,
            completion.model,
            prefix,
            maxTokens,
            completionMode
          );
        }

        // Clean up the suggestion
        result = result.trim();

        if (completionMode === 'code') {
          // Code mode: take only first line for cleaner suggestions
          result = result.split('\n')[0];
        } else {
          // Prompt mode: allow multi-line but clean up excessive whitespace
          result = result.replace(/\n{3,}/g, '\n\n'); // Max 2 consecutive newlines
          // Limit to ~3 lines to keep it readable
          const lines = result.split('\n');
          if (lines.length > 3) {
            result = lines.slice(0, 3).join('\n') + '...';
          }
        }

        setSuggestion(result || '');
      } catch (err) {
        console.error('Completion error:', err);
        setCompletionError(err instanceof Error ? err.message : 'Failed to fetch completion');
        setSuggestion('');
      } finally {
        setIsLoadingSuggestion(false);
      }
    }, debounceMs);

    return () => {
      clearTimeout(timer);
      if (completionAbortRef.current) {
        completionAbortRef.current.abort();
      }
    };
  }, [localValue, mode, vimMode, completion]);

  // Keep cursor/selection position in sync
  useEffect(() => {
    if (!textareaRef.current || !vimMode) return;

    if (mode === 'normal') {
      textareaRef.current.setSelectionRange(cursorPos, cursorPos + 1);
    } else if (mode === 'visual-char') {
      const start = Math.min(visualStart, cursorPos);
      const end = Math.max(visualStart, cursorPos) + 1;
      textareaRef.current.setSelectionRange(start, end);
    } else if (mode === 'visual-line') {
      const startLine = findLineStart(Math.min(visualStart, cursorPos));
      const endLine = findLineEnd(Math.max(visualStart, cursorPos));
      textareaRef.current.setSelectionRange(startLine, endLine);
    }
  }, [cursorPos, visualStart, vimMode, mode]);

  const findLineStart = useCallback((pos: number) => {
    const text = localValue;
    let p = pos;
    while (p > 0 && text[p - 1] !== '\n') p--;
    return p;
  }, [localValue]);

  const findLineEnd = useCallback((pos: number) => {
    const text = localValue;
    let p = pos;
    while (p < text.length && text[p] !== '\n') p++;
    return p;
  }, [localValue]);

  const moveCursor = useCallback((newPos: number) => {
    const maxPos = Math.max(0, localValue.length - 1);
    const clampedPos = Math.max(0, Math.min(newPos, maxPos));
    setCursorPos(clampedPos);
    if (textareaRef.current && mode === 'normal') {
      textareaRef.current.setSelectionRange(clampedPos, clampedPos + 1);
    }
  }, [localValue.length, mode]);

  const findWordStart = useCallback((pos: number, backward: boolean) => {
    const text = localValue;
    if (backward) {
      let p = pos - 1;
      while (p > 0 && /\s/.test(text[p])) p--;
      while (p > 0 && !/\s/.test(text[p - 1])) p--;
      return Math.max(0, p);
    } else {
      let p = pos;
      while (p < text.length && !/\s/.test(text[p])) p++;
      while (p < text.length && /\s/.test(text[p])) p++;
      return Math.min(text.length - 1, p);
    }
  }, [localValue]);

  const findWordEnd = useCallback((pos: number) => {
    const text = localValue;
    let p = pos;
    while (p < text.length && /\s/.test(text[p])) p++;
    while (p < text.length - 1 && !/\s/.test(text[p + 1])) p++;
    return Math.min(text.length - 1, p);
  }, [localValue]);

  const getVisualSelection = useCallback(() => {
    if (mode === 'visual-char') {
      const start = Math.min(visualStart, cursorPos);
      const end = Math.max(visualStart, cursorPos) + 1;
      return { start, end, text: localValue.slice(start, end) };
    } else if (mode === 'visual-line') {
      const startLine = findLineStart(Math.min(visualStart, cursorPos));
      let endLine = findLineEnd(Math.max(visualStart, cursorPos));
      if (endLine < localValue.length && localValue[endLine] === '\n') endLine++;
      return { start: startLine, end: endLine, text: localValue.slice(startLine, endLine) };
    }
    return { start: cursorPos, end: cursorPos, text: '' };
  }, [mode, visualStart, cursorPos, localValue, findLineStart, findLineEnd]);

  const deleteSelection = useCallback(() => {
    const { start, end, text } = getVisualSelection();
    setYankBuffer(text);
    setYankType(mode === 'visual-line' ? 'line' : 'char');
    const newValue = localValue.slice(0, start) + localValue.slice(end);
    syncToParent(newValue);
    moveCursor(Math.min(start, Math.max(0, newValue.length - 1)));
    setMode('normal');
  }, [getVisualSelection, mode, localValue, syncToParent, moveCursor]);

  const yankSelection = useCallback(() => {
    const { text } = getVisualSelection();
    setYankBuffer(text);
    setYankType(mode === 'visual-line' ? 'line' : 'char');
    setMode('normal');
  }, [getVisualSelection, mode]);

  const deleteLine = useCallback(() => {
    const lineStart = findLineStart(cursorPos);
    let lineEnd = findLineEnd(cursorPos);
    if (lineEnd < localValue.length && localValue[lineEnd] === '\n') lineEnd++;
    const line = localValue.slice(lineStart, lineEnd);
    setYankBuffer(line);
    setYankType('line');
    const newValue = localValue.slice(0, lineStart) + localValue.slice(lineEnd);
    syncToParent(newValue);
    moveCursor(Math.min(lineStart, Math.max(0, newValue.length - 1)));
  }, [cursorPos, localValue, syncToParent, findLineStart, findLineEnd, moveCursor]);

  const yankLine = useCallback(() => {
    const lineStart = findLineStart(cursorPos);
    const lineEnd = findLineEnd(cursorPos);
    const text = localValue.slice(lineStart, lineEnd);
    setYankBuffer(text + '\n');
    setYankType('line');
  }, [cursorPos, localValue, findLineStart, findLineEnd]);

  const paste = useCallback((after: boolean) => {
    if (!yankBuffer) return;
    let insertPos = cursorPos;
    if (yankType === 'line') {
      if (after) {
        insertPos = findLineEnd(cursorPos);
        if (insertPos < localValue.length) insertPos++;
      } else {
        insertPos = findLineStart(cursorPos);
      }
      const textToInsert = yankBuffer.endsWith('\n') ? yankBuffer : yankBuffer + '\n';
      const newValue = localValue.slice(0, insertPos) + textToInsert + localValue.slice(insertPos);
      syncToParent(newValue);
      moveCursor(insertPos);
    } else {
      if (after && localValue.length > 0) {
        insertPos = cursorPos + 1;
      }
      const newValue = localValue.slice(0, insertPos) + yankBuffer + localValue.slice(insertPos);
      syncToParent(newValue);
      moveCursor(insertPos + yankBuffer.length - 1);
    }
  }, [yankBuffer, yankType, cursorPos, localValue, syncToParent, findLineStart, findLineEnd, moveCursor]);

  const acceptSuggestion = useCallback(() => {
    if (!suggestion) return false;
    const textarea = textareaRef.current;
    if (!textarea) return false;

    const cursorPosition = textarea.selectionStart;
    const newValue = localValue.slice(0, cursorPosition) + suggestion + localValue.slice(cursorPosition);
    syncToParent(newValue);
    setSuggestion('');

    // Move cursor to end of inserted suggestion
    setTimeout(() => {
      if (textareaRef.current) {
        const newPos = cursorPosition + suggestion.length;
        textareaRef.current.setSelectionRange(newPos, newPos);
        setCursorPos(newPos);
      }
    }, 0);

    return true;
  }, [suggestion, localValue, syncToParent]);

  const handleMovement = useCallback((key: string, e: KeyboardEvent<HTMLTextAreaElement>) => {
    let newPos = cursorPos;

    switch (key) {
      case 'h':
      case 'ArrowLeft':
        newPos = Math.max(0, cursorPos - 1);
        break;
      case 'l':
      case 'ArrowRight':
        newPos = Math.min(localValue.length - 1, cursorPos + 1);
        break;
      case 'j':
      case 'ArrowDown': {
        const currentLineStart = findLineStart(cursorPos);
        const colOffset = cursorPos - currentLineStart;
        const nextLineStart = findLineEnd(cursorPos) + 1;
        if (nextLineStart < localValue.length) {
          const nextLineEnd = findLineEnd(nextLineStart);
          const nextLineLen = nextLineEnd - nextLineStart;
          newPos = nextLineStart + Math.min(colOffset, nextLineLen);
        }
        break;
      }
      case 'k':
      case 'ArrowUp': {
        const currLineStart = findLineStart(cursorPos);
        if (currLineStart > 0) {
          const colOff = cursorPos - currLineStart;
          const prevLineEnd = currLineStart - 1;
          const prevLineStart = findLineStart(prevLineEnd);
          const prevLineLen = prevLineEnd - prevLineStart;
          newPos = prevLineStart + Math.min(colOff, prevLineLen);
        }
        break;
      }
      case 'w':
        newPos = findWordStart(cursorPos, false);
        break;
      case 'b':
        newPos = findWordStart(cursorPos, true);
        break;
      case 'e':
        newPos = findWordEnd(cursorPos);
        break;
      case '0':
        newPos = findLineStart(cursorPos);
        break;
      case '$':
        newPos = Math.max(0, findLineEnd(cursorPos) - 1);
        break;
      case 'G':
        newPos = Math.max(0, localValue.length - 1);
        break;
      case 'g':
        if (e.shiftKey) {
          newPos = Math.max(0, localValue.length - 1);
        }
        break;
      default:
        return false;
    }

    setCursorPos(newPos);
    return true;
  }, [cursorPos, localValue, findLineStart, findLineEnd, findWordStart, findWordEnd]);

  const handleNormalModeKey = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    const key = e.key;

    if (pendingCommand) {
      if (pendingCommand === 'd' && key === 'd') {
        deleteLine();
        setPendingCommand('');
        e.preventDefault();
        return;
      }
      if (pendingCommand === 'y' && key === 'y') {
        yankLine();
        setPendingCommand('');
        e.preventDefault();
        return;
      }
      setPendingCommand('');
    }

    if (key === 'v' && !e.shiftKey) {
      setMode('visual-char');
      setVisualStart(cursorPos);
      e.preventDefault();
      return;
    }
    if (key === 'V' || (key === 'v' && e.shiftKey)) {
      setMode('visual-line');
      setVisualStart(cursorPos);
      e.preventDefault();
      return;
    }

    switch (key) {
      case 'i':
        setMode('insert');
        e.preventDefault();
        break;
      case 'a':
        setMode('insert');
        moveCursor(cursorPos + 1);
        e.preventDefault();
        break;
      case 'A':
        setMode('insert');
        moveCursor(findLineEnd(cursorPos));
        e.preventDefault();
        break;
      case 'I':
        setMode('insert');
        moveCursor(findLineStart(cursorPos));
        e.preventDefault();
        break;
      case 'o': {
        setMode('insert');
        const lineEnd = findLineEnd(cursorPos);
        syncToParent(localValue.slice(0, lineEnd) + '\n' + localValue.slice(lineEnd));
        moveCursor(lineEnd + 1);
        e.preventDefault();
        break;
      }
      case 'O': {
        setMode('insert');
        const lineStart = findLineStart(cursorPos);
        syncToParent(localValue.slice(0, lineStart) + '\n' + localValue.slice(lineStart));
        moveCursor(lineStart);
        e.preventDefault();
        break;
      }
      case 'x':
        if (localValue.length > 0) {
          setYankBuffer(localValue[cursorPos] || '');
          setYankType('char');
          syncToParent(localValue.slice(0, cursorPos) + localValue.slice(cursorPos + 1));
          moveCursor(Math.min(cursorPos, Math.max(0, localValue.length - 2)));
        }
        e.preventDefault();
        break;
      case 'd':
        setPendingCommand('d');
        e.preventDefault();
        break;
      case 'y':
        setPendingCommand('y');
        e.preventDefault();
        break;
      case 'p':
        paste(true);
        e.preventDefault();
        break;
      case 'P':
        paste(false);
        e.preventDefault();
        break;
      case 'u':
        e.preventDefault();
        break;
      case 'Enter':
        if (e.metaKey || e.ctrlKey) {
          onSubmit?.();
        }
        e.preventDefault();
        break;
      default:
        if (handleMovement(key, e)) {
          e.preventDefault();
        } else {
          e.preventDefault();
        }
    }
  }, [cursorPos, localValue, syncToParent, moveCursor, findLineStart, findLineEnd, deleteLine, yankLine, paste, pendingCommand, onSubmit, handleMovement]);

  const handleVisualModeKey = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    const key = e.key;

    if (key === 'Escape') {
      setMode('normal');
      e.preventDefault();
      return;
    }

    if (key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      onSubmit?.();
      e.preventDefault();
      return;
    }

    if (key === 'v' && !e.shiftKey && mode === 'visual-line') {
      setMode('visual-char');
      e.preventDefault();
      return;
    }
    if ((key === 'V' || (key === 'v' && e.shiftKey)) && mode === 'visual-char') {
      setMode('visual-line');
      e.preventDefault();
      return;
    }

    if (key === 'd' || key === 'x') {
      deleteSelection();
      e.preventDefault();
      return;
    }
    if (key === 'y') {
      yankSelection();
      e.preventDefault();
      return;
    }

    if (handleMovement(key, e)) {
      e.preventDefault();
      return;
    }

    e.preventDefault();
  }, [mode, onSubmit, deleteSelection, yankSelection, handleMovement]);

  const handleInsertModeKey = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Escape') {
      setMode('normal');
      moveCursor(Math.max(0, cursorPos - 1));
      setSuggestion('');
      e.preventDefault();
      return;
    }

    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      onSubmit?.();
      e.preventDefault();
      return;
    }

    // Tab to accept suggestion
    if (e.key === 'Tab' && suggestion) {
      e.preventDefault();
      acceptSuggestion();
      return;
    }
  }, [moveCursor, cursorPos, onSubmit, suggestion, acceptSuggestion]);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!vimMode) {
      // Non-vim mode: Tab accepts suggestion
      if (e.key === 'Tab' && suggestion) {
        e.preventDefault();
        acceptSuggestion();
        return;
      }
      if (e.key === 'Escape') {
        setSuggestion('');
        return;
      }
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onSubmit?.();
      }
      return;
    }

    if (mode === 'normal') {
      handleNormalModeKey(e);
    } else if (mode === 'insert') {
      handleInsertModeKey(e);
    } else if (mode === 'visual-char' || mode === 'visual-line') {
      handleVisualModeKey(e);
    }
  }, [vimMode, mode, handleNormalModeKey, handleInsertModeKey, handleVisualModeKey, onSubmit, suggestion, acceptSuggestion]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    syncToParent(e.target.value);
    if (vimMode && mode === 'insert') {
      setCursorPos(e.target.selectionStart);
    }
  }, [syncToParent, vimMode, mode]);

  const handleClick = useCallback(() => {
    if (textareaRef.current) {
      setCursorPos(textareaRef.current.selectionStart);
    }
  }, []);

  const handleScroll = useCallback(() => {
    // Sync overlay scroll with textarea
    if (textareaRef.current && overlayRef.current) {
      overlayRef.current.scrollTop = textareaRef.current.scrollTop;
      overlayRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }, []);

  const getModeDisplay = () => {
    switch (mode) {
      case 'normal': return 'NORMAL';
      case 'insert': return 'INSERT';
      case 'visual-char': return 'VISUAL';
      case 'visual-line': return 'V-LINE';
    }
  };

  const getModeColor = () => {
    switch (mode) {
      case 'normal': return 'bg-blue-600 text-white';
      case 'insert': return 'bg-green-600 text-white';
      case 'visual-char':
      case 'visual-line': return 'bg-purple-600 text-white';
    }
  };

  // Render ghost text overlay
  const renderGhostText = () => {
    if (!suggestion || !textareaRef.current) return null;

    const textarea = textareaRef.current;
    const cursorPosition = textarea.selectionStart;
    const textBeforeCursor = localValue.slice(0, cursorPosition);
    const textAfterCursor = localValue.slice(cursorPosition);

    return (
      <div
        ref={overlayRef}
        className="absolute inset-0 pointer-events-none overflow-hidden whitespace-pre-wrap break-words font-mono text-sm p-3"
        style={{
          color: 'transparent',
        }}
      >
        {/* Text before cursor (invisible, for positioning) */}
        <span>{textBeforeCursor}</span>
        {/* Ghost text suggestion */}
        <span className="text-gray-500 opacity-60">{suggestion}</span>
        {/* Text after cursor (invisible) */}
        <span>{textAfterCursor}</span>
      </div>
    );
  };

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-2 py-1 bg-gray-800 border border-gray-700 border-b-0 rounded-t">
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={vimMode}
              onChange={(e) => onVimModeToggle(e.target.checked)}
              className="rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900 w-3 h-3"
            />
            Vim
          </label>
          {vimMode && (
            <span className={`px-1.5 py-0.5 text-[10px] font-mono font-bold rounded ${getModeColor()}`}>
              {getModeDisplay()}
            </span>
          )}
          {vimMode && pendingCommand && (
            <span className="text-[10px] text-yellow-400 font-mono">{pendingCommand}</span>
          )}
          {completion?.enabled && (
            <span className="flex items-center gap-1 text-[10px] text-gray-500" title={completionError || undefined}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                completionError ? 'bg-red-500' :
                isLoadingSuggestion ? 'bg-yellow-400 animate-pulse' : 'bg-green-500'
              }`} />
              {completionError ? 'Error' : completion.model.split(':')[0]}
            </span>
          )}
        </div>
        <span className="text-[10px] text-gray-500">
          {vimMode
            ? 'Esc: normal, i: insert, v: visual, V: v-line'
            : suggestion
              ? 'Tab: accept, Esc: dismiss'
              : 'Cmd/Ctrl+Enter to send'}
        </span>
      </div>

      {/* Textarea with ghost text overlay */}
      <div className="relative">
        {suggestion && renderGhostText()}
        <textarea
          ref={textareaRef}
          value={localValue}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onClick={handleClick}
          onScroll={handleScroll}
          placeholder={placeholder}
          disabled={disabled}
          className={`w-full bg-gray-900 border border-gray-700 rounded-b text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none font-mono ${
            vimMode ? 'h-48 p-3' : 'h-20 p-2'
          } ${vimMode && mode === 'normal' ? 'caret-transparent' : ''} ${
            suggestion ? 'bg-transparent relative z-10' : ''
          }`}
          style={vimMode && mode === 'normal' ? { caretColor: 'transparent' } : undefined}
        />
      </div>

      {/* Help text */}
      {vimMode && (
        <div className="text-[10px] text-gray-600 mt-1 px-1">
          hjkl: move | w/b/e: word | 0/$: line | i/a/o: insert | v: visual | V: v-line | d/y: del/yank | p: paste | Tab: accept | Cmd+Enter: send
        </div>
      )}
    </div>
  );
}

export default VimTextarea;
