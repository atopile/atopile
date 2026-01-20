import { useState } from 'react';
import { FileText, ChevronDown, ChevronRight, Shield, Terminal } from 'lucide-react';

interface AllowedPrompt {
  tool: string;
  prompt: string;
}

interface ExitPlanModeInput {
  allowedPrompts?: AllowedPrompt[];
  plan?: string;
}

interface PlanModeDisplayProps {
  toolInput: ExitPlanModeInput;
  timestamp?: string;
}

// Simple markdown-like rendering for plan text
function renderPlanText(text: string): React.ReactNode {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeContent: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Handle code blocks
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`} className="bg-gray-800 rounded p-2 my-2 overflow-x-auto text-xs font-mono text-gray-300">
            {codeContent.join('\n')}
          </pre>
        );
        codeContent = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent.push(line);
      continue;
    }

    // Headers
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="text-sm font-medium text-gray-400 mt-2 mb-1">
          {line.slice(4)}
        </h3>
      );
    } else if (line.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="text-base font-semibold text-gray-300 mt-3 mb-2">
          {line.slice(3)}
        </h2>
      );
    } else if (line.startsWith('# ')) {
      elements.push(
        <h1 key={i} className="text-lg font-bold text-gray-200 mt-4 mb-2">
          {line.slice(2)}
        </h1>
      );
    }
    // List items
    else if (line.match(/^[\s]*[-*]\s/)) {
      const indent = line.match(/^(\s*)/)?.[1]?.length || 0;
      const content = line.replace(/^[\s]*[-*]\s/, '');
      elements.push(
        <div key={i} className="text-sm text-gray-300 my-0.5" style={{ paddingLeft: `${indent * 4 + 16}px` }}>
          <span className="text-gray-500 mr-2">•</span>
          {content}
        </div>
      );
    }
    // Numbered list items
    else if (line.match(/^[\s]*\d+\.\s/)) {
      const match = line.match(/^([\s]*)(\d+)\.\s(.*)$/);
      if (match) {
        const indent = match[1].length;
        const num = match[2];
        const content = match[3];
        elements.push(
          <div key={i} className="text-sm text-gray-300 my-0.5" style={{ paddingLeft: `${indent * 4 + 16}px` }}>
            <span className="text-gray-500 mr-2">{num}.</span>
            {content}
          </div>
        );
      }
    }
    // Empty line
    else if (line.trim() === '') {
      elements.push(<div key={i} className="h-2" />);
    }
    // Regular paragraph
    else {
      // Handle inline code
      const parts = line.split(/(`[^`]+`)/g);
      const rendered = parts.map((part, partIdx) => {
        if (part.startsWith('`') && part.endsWith('`')) {
          return (
            <code key={partIdx} className="text-xs bg-gray-800 px-1 py-0.5 rounded text-blue-300">
              {part.slice(1, -1)}
            </code>
          );
        }
        return part;
      });
      elements.push(
        <p key={i} className="text-sm text-gray-300 my-1">
          {rendered}
        </p>
      );
    }
  }

  // Handle unclosed code block
  if (inCodeBlock && codeContent.length > 0) {
    elements.push(
      <pre key="code-final" className="bg-gray-800 rounded p-2 my-2 overflow-x-auto text-xs font-mono text-gray-300">
        {codeContent.join('\n')}
      </pre>
    );
  }

  return elements;
}

export function PlanModeDisplay({ toolInput, timestamp }: PlanModeDisplayProps) {
  const [planExpanded, setPlanExpanded] = useState(true);
  const [permissionsExpanded, setPermissionsExpanded] = useState(false);

  const allowedPrompts = toolInput.allowedPrompts || [];
  const plan = toolInput.plan || '';

  return (
    <div className="py-2 pl-11">
      <div className="rounded-lg border border-blue-500/30 bg-blue-500/5 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 bg-blue-500/10 border-b border-blue-500/20">
          <FileText className="w-4 h-4 text-blue-400" />
          <span className="font-medium text-blue-400">Implementation Plan</span>
          {timestamp && (
            <span className="text-[10px] text-gray-600 font-mono ml-auto">{timestamp}</span>
          )}
        </div>

        {/* Plan Content */}
        {plan && (
          <div className="border-b border-blue-500/20">
            <div
              className="flex items-center gap-2 px-4 py-2 cursor-pointer hover:bg-blue-500/5"
              onClick={() => setPlanExpanded(!planExpanded)}
            >
              {planExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-500" />
              )}
              <span className="text-sm text-gray-400">Plan Details</span>
            </div>
            {planExpanded && (
              <div className="px-4 pb-4">
                {renderPlanText(plan)}
              </div>
            )}
          </div>
        )}

        {/* Requested Permissions */}
        {allowedPrompts.length > 0 && (
          <div>
            <div
              className="flex items-center gap-2 px-4 py-2 cursor-pointer hover:bg-blue-500/5"
              onClick={() => setPermissionsExpanded(!permissionsExpanded)}
            >
              {permissionsExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-500" />
              )}
              <Shield className="w-3.5 h-3.5 text-yellow-500" />
              <span className="text-sm text-gray-400">
                Requested Permissions ({allowedPrompts.length})
              </span>
            </div>
            {permissionsExpanded && (
              <div className="px-4 pb-3 space-y-1.5">
                {allowedPrompts.map((prompt, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-800/50 rounded border border-gray-700/50"
                  >
                    <Terminal className="w-3.5 h-3.5 text-gray-500" />
                    <span className="text-xs font-mono text-yellow-400">{prompt.tool}</span>
                    <span className="text-xs text-gray-500">:</span>
                    <span className="text-xs text-gray-300">{prompt.prompt}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Status indicator */}
        <div className="px-4 py-2 bg-yellow-500/10 border-t border-yellow-500/20">
          <span className="text-xs text-yellow-400">
            Awaiting user approval to proceed with implementation
          </span>
        </div>
      </div>
    </div>
  );
}

export default PlanModeDisplay;
