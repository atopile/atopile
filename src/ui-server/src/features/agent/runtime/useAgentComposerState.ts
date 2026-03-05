import { useCallback, useMemo, useRef, useState } from 'react';
import type { ModuleDefinition } from '../../../types/build';
import { buildMentionItems, findMentionToken, type MentionItem, type MentionToken } from './shared';

export function useAgentComposerState(
  projectModules: ModuleDefinition[],
  projectFiles: string[],
  options?: { isLoadingModules?: boolean; isLoadingFiles?: boolean },
) {
  const composerInputRef = useRef<HTMLTextAreaElement | null>(null);
  const [input, setInput] = useState('');
  const [mentionToken, setMentionToken] = useState<MentionToken | null>(null);
  const [mentionIndex, setMentionIndex] = useState(0);
  const isLoadingMentions = Boolean(
    mentionToken
      && ((options?.isLoadingModules && projectModules.length === 0)
        || (options?.isLoadingFiles && projectFiles.length === 0)),
  );

  const mentionItems = useMemo(
    () => buildMentionItems(mentionToken, projectModules, projectFiles),
    [mentionToken, projectFiles, projectModules],
  );

  const refreshMentionFromInput = useCallback((nextInput: string, caret: number) => {
    setMentionToken(findMentionToken(nextInput, caret));
    setMentionIndex(0);
  }, []);

  const insertMention = useCallback((item: MentionItem) => {
    if (!mentionToken) return;
    const before = input.slice(0, mentionToken.start);
    const after = input.slice(mentionToken.end);
    const mentionText = `@${item.token}`;
    const needsSpace = after.length > 0 && !/^\s/.test(after);
    const nextInput = `${before}${mentionText}${needsSpace ? ' ' : ''}${after}`;
    const cursor = (before + mentionText + (needsSpace ? ' ' : '')).length;

    setInput(nextInput);
    setMentionToken(null);
    setMentionIndex(0);
    requestAnimationFrame(() => {
      const element = composerInputRef.current;
      if (!element) return;
      element.focus();
      element.setSelectionRange(cursor, cursor);
    });
  }, [input, mentionToken]);

  return {
    composerInputRef,
    input,
    setInput,
    mentionToken,
    setMentionToken,
    mentionItems,
    isLoadingMentions,
    mentionIndex,
    setMentionIndex,
    refreshMentionFromInput,
    insertMention,
  };
}
