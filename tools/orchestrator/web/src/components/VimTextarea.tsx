import { useState, useRef, useCallback, useEffect, KeyboardEvent } from 'react';

type VimMode = 'normal' | 'insert' | 'visual-char' | 'visual-line';

interface VimTextareaProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  vimMode: boolean;
  onVimModeToggle: (enabled: boolean) => void;
  className?: string;
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
}: VimTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [mode, setMode] = useState<VimMode>('normal');
  const [cursorPos, setCursorPos] = useState(0);
  const [yankBuffer, setYankBuffer] = useState('');
  const [yankType, setYankType] = useState<'char' | 'line'>('char');
  const [pendingCommand, setPendingCommand] = useState('');
  const [visualStart, setVisualStart] = useState(0);

  // Reset to normal mode when vim mode is enabled
  useEffect(() => {
    if (vimMode) {
      setMode('normal');
    }
  }, [vimMode]);

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
    const text = value;
    let p = pos;
    while (p > 0 && text[p - 1] !== '\n') p--;
    return p;
  }, [value]);

  const findLineEnd = useCallback((pos: number) => {
    const text = value;
    let p = pos;
    while (p < text.length && text[p] !== '\n') p++;
    return p;
  }, [value]);

  const moveCursor = useCallback((newPos: number) => {
    const maxPos = Math.max(0, value.length - 1);
    const clampedPos = Math.max(0, Math.min(newPos, maxPos));
    setCursorPos(clampedPos);
    if (textareaRef.current && mode === 'normal') {
      textareaRef.current.setSelectionRange(clampedPos, clampedPos + 1);
    }
  }, [value.length, mode]);

  const findWordStart = useCallback((pos: number, backward: boolean) => {
    const text = value;
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
  }, [value]);

  const findWordEnd = useCallback((pos: number) => {
    const text = value;
    let p = pos;
    while (p < text.length && /\s/.test(text[p])) p++;
    while (p < text.length - 1 && !/\s/.test(text[p + 1])) p++;
    return Math.min(text.length - 1, p);
  }, [value]);

  const getVisualSelection = useCallback(() => {
    if (mode === 'visual-char') {
      const start = Math.min(visualStart, cursorPos);
      const end = Math.max(visualStart, cursorPos) + 1;
      return { start, end, text: value.slice(start, end) };
    } else if (mode === 'visual-line') {
      const startLine = findLineStart(Math.min(visualStart, cursorPos));
      let endLine = findLineEnd(Math.max(visualStart, cursorPos));
      // Include the newline if there is one
      if (endLine < value.length && value[endLine] === '\n') endLine++;
      return { start: startLine, end: endLine, text: value.slice(startLine, endLine) };
    }
    return { start: cursorPos, end: cursorPos, text: '' };
  }, [mode, visualStart, cursorPos, value, findLineStart, findLineEnd]);

  const deleteSelection = useCallback(() => {
    const { start, end, text } = getVisualSelection();
    setYankBuffer(text);
    setYankType(mode === 'visual-line' ? 'line' : 'char');
    const newValue = value.slice(0, start) + value.slice(end);
    onChange(newValue);
    moveCursor(Math.min(start, Math.max(0, newValue.length - 1)));
    setMode('normal');
  }, [getVisualSelection, mode, value, onChange, moveCursor]);

  const yankSelection = useCallback(() => {
    const { text } = getVisualSelection();
    setYankBuffer(text);
    setYankType(mode === 'visual-line' ? 'line' : 'char');
    setMode('normal');
  }, [getVisualSelection, mode]);

  const deleteLine = useCallback(() => {
    const lineStart = findLineStart(cursorPos);
    let lineEnd = findLineEnd(cursorPos);
    if (lineEnd < value.length && value[lineEnd] === '\n') lineEnd++;
    const line = value.slice(lineStart, lineEnd);
    setYankBuffer(line);
    setYankType('line');
    const newValue = value.slice(0, lineStart) + value.slice(lineEnd);
    onChange(newValue);
    moveCursor(Math.min(lineStart, Math.max(0, newValue.length - 1)));
  }, [cursorPos, value, onChange, findLineStart, findLineEnd, moveCursor]);

  const yankLine = useCallback(() => {
    const lineStart = findLineStart(cursorPos);
    const lineEnd = findLineEnd(cursorPos);
    const text = value.slice(lineStart, lineEnd);
    setYankBuffer(text + '\n');
    setYankType('line');
  }, [cursorPos, value, findLineStart, findLineEnd]);

  const paste = useCallback((after: boolean) => {
    if (!yankBuffer) return;
    let insertPos = cursorPos;
    if (yankType === 'line') {
      if (after) {
        insertPos = findLineEnd(cursorPos);
        if (insertPos < value.length) insertPos++;
      } else {
        insertPos = findLineStart(cursorPos);
      }
      const textToInsert = yankBuffer.endsWith('\n') ? yankBuffer : yankBuffer + '\n';
      const newValue = value.slice(0, insertPos) + textToInsert + value.slice(insertPos);
      onChange(newValue);
      moveCursor(insertPos);
    } else {
      if (after && value.length > 0) {
        insertPos = cursorPos + 1;
      }
      const newValue = value.slice(0, insertPos) + yankBuffer + value.slice(insertPos);
      onChange(newValue);
      moveCursor(insertPos + yankBuffer.length - 1);
    }
  }, [yankBuffer, yankType, cursorPos, value, onChange, findLineStart, findLineEnd, moveCursor]);

  const handleMovement = useCallback((key: string, e: KeyboardEvent<HTMLTextAreaElement>) => {
    let newPos = cursorPos;

    switch (key) {
      case 'h':
      case 'ArrowLeft':
        newPos = Math.max(0, cursorPos - 1);
        break;
      case 'l':
      case 'ArrowRight':
        newPos = Math.min(value.length - 1, cursorPos + 1);
        break;
      case 'j':
      case 'ArrowDown': {
        const currentLineStart = findLineStart(cursorPos);
        const colOffset = cursorPos - currentLineStart;
        const nextLineStart = findLineEnd(cursorPos) + 1;
        if (nextLineStart < value.length) {
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
        newPos = Math.max(0, value.length - 1);
        break;
      case 'g':
        if (e.shiftKey) {
          newPos = Math.max(0, value.length - 1);
        }
        break;
      default:
        return false;
    }

    setCursorPos(newPos);
    return true;
  }, [cursorPos, value, findLineStart, findLineEnd, findWordStart, findWordEnd]);

  const handleNormalModeKey = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    const key = e.key;

    // Handle pending commands (like dd, yy)
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

    // Visual mode entry
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
      // Mode switching
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
        onChange(value.slice(0, lineEnd) + '\n' + value.slice(lineEnd));
        moveCursor(lineEnd + 1);
        e.preventDefault();
        break;
      }
      case 'O': {
        setMode('insert');
        const lineStart = findLineStart(cursorPos);
        onChange(value.slice(0, lineStart) + '\n' + value.slice(lineStart));
        moveCursor(lineStart);
        e.preventDefault();
        break;
      }

      // Editing
      case 'x':
        if (value.length > 0) {
          setYankBuffer(value[cursorPos] || '');
          setYankType('char');
          onChange(value.slice(0, cursorPos) + value.slice(cursorPos + 1));
          moveCursor(Math.min(cursorPos, Math.max(0, value.length - 2)));
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

      // Submit
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
  }, [cursorPos, value, onChange, moveCursor, findLineStart, findLineEnd, deleteLine, yankLine, paste, pendingCommand, onSubmit, handleMovement]);

  const handleVisualModeKey = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    const key = e.key;

    // Escape to normal mode
    if (key === 'Escape') {
      setMode('normal');
      e.preventDefault();
      return;
    }

    // Submit with Cmd/Ctrl+Enter
    if (key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      onSubmit?.();
      e.preventDefault();
      return;
    }

    // Switch between visual modes
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

    // Operations on selection
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

    // Movement extends selection
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
      e.preventDefault();
      return;
    }

    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      onSubmit?.();
      e.preventDefault();
      return;
    }
  }, [moveCursor, cursorPos, onSubmit]);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!vimMode) {
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
  }, [vimMode, mode, handleNormalModeKey, handleInsertModeKey, handleVisualModeKey, onSubmit]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
    if (vimMode && mode === 'insert') {
      setCursorPos(e.target.selectionStart);
    }
  }, [onChange, vimMode, mode]);

  const handleClick = useCallback(() => {
    if (textareaRef.current) {
      setCursorPos(textareaRef.current.selectionStart);
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
        </div>
        <span className="text-[10px] text-gray-500">
          {vimMode ? 'Esc: normal, i: insert, v: visual, V: v-line' : 'Cmd/Ctrl+Enter to send'}
        </span>
      </div>

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onClick={handleClick}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full bg-gray-900 border border-gray-700 rounded-b text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none font-mono ${
          vimMode ? 'h-48 p-3' : 'h-20 p-2'
        } ${vimMode && mode === 'normal' ? 'caret-transparent' : ''}`}
        style={vimMode && mode === 'normal' ? { caretColor: 'transparent' } : undefined}
      />

      {/* Help text */}
      {vimMode && (
        <div className="text-[10px] text-gray-600 mt-1 px-1">
          hjkl: move | w/b/e: word | 0/$: line | i/a/o: insert | v: visual | V: v-line | d/y: del/yank | p: paste | Cmd+Enter: send
        </div>
      )}
    </div>
  );
}

export default VimTextarea;
