import { useState, useCallback } from 'react';
import { HelpCircle, ChevronDown, ChevronRight, CheckCircle2, Circle, Send, Edit3 } from 'lucide-react';

interface QuestionOption {
  label: string;
  description?: string;
}

interface Question {
  question: string;
  header?: string;
  options: QuestionOption[];
  multiSelect?: boolean;
}

interface AskUserQuestionInput {
  questions: Question[];
  answers?: Record<string, string>;
  metadata?: {
    source?: string;
  };
}

interface QuestionDisplayProps {
  toolInput: AskUserQuestionInput;
  timestamp?: string;
  onSendResponse?: (response: string) => void;
  isAgentRunning?: boolean;
  responded?: boolean;
}

interface QuestionCardProps {
  question: Question;
  questionIndex: number;
  selectedOptions: Set<number>;
  customText: string;
  onOptionSelect: (optIndex: number) => void;
  onCustomTextChange: (text: string) => void;
  isOtherSelected: boolean;
  onOtherSelect: () => void;
  disabled?: boolean;
}

function QuestionCard({
  question,
  selectedOptions,
  customText,
  onOptionSelect,
  onCustomTextChange,
  isOtherSelected,
  onOtherSelect,
  disabled,
}: QuestionCardProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="border border-purple-500/30 rounded-lg overflow-hidden bg-purple-500/5">
      <div
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-purple-500/10"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-500" />
        )}
        {question.header && (
          <span className="text-xs font-medium px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded">
            {question.header}
          </span>
        )}
        <span className="text-sm text-gray-200 flex-1">{question.question}</span>
        {question.multiSelect && (
          <span className="text-[10px] text-gray-500">(multi-select)</span>
        )}
      </div>
      {expanded && (
        <div className="px-3 pb-3 space-y-1.5">
          {question.options.map((option, optIndex) => {
            const isSelected = selectedOptions.has(optIndex);
            return (
              <button
                key={optIndex}
                className={`w-full flex items-start gap-2 px-3 py-2 rounded border transition-all text-left ${
                  isSelected
                    ? 'bg-purple-500/20 border-purple-500/50'
                    : 'bg-gray-800/50 border-gray-700/50 hover:border-purple-500/30'
                } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                onClick={() => !disabled && onOptionSelect(optIndex)}
                disabled={disabled}
              >
                {question.multiSelect ? (
                  <CheckCircle2 className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isSelected ? 'text-purple-400' : 'text-gray-600'}`} />
                ) : (
                  <Circle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isSelected ? 'text-purple-400 fill-purple-400' : 'text-gray-600'}`} />
                )}
                <div className="flex-1 min-w-0">
                  <div className={`text-sm ${isSelected ? 'text-purple-200' : 'text-gray-200'}`}>{option.label}</div>
                  {option.description && (
                    <div className="text-xs text-gray-500 mt-0.5">{option.description}</div>
                  )}
                </div>
              </button>
            );
          })}
          {/* Other option */}
          <div
            className={`rounded border transition-all ${
              isOtherSelected
                ? 'bg-purple-500/20 border-purple-500/50'
                : 'bg-gray-800/30 border-dashed border-gray-700/50'
            } ${disabled ? 'opacity-50' : ''}`}
          >
            <button
              className={`w-full flex items-center gap-2 px-3 py-2 text-left ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
              onClick={() => !disabled && onOtherSelect()}
              disabled={disabled}
            >
              <Edit3 className={`w-4 h-4 flex-shrink-0 ${isOtherSelected ? 'text-purple-400' : 'text-gray-600'}`} />
              <span className={`text-sm ${isOtherSelected ? 'text-purple-200' : 'text-gray-500'}`}>
                Other (custom response)
              </span>
            </button>
            {isOtherSelected && (
              <div className="px-3 pb-3">
                <input
                  type="text"
                  className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded focus:border-purple-500 focus:outline-none"
                  placeholder="Type your response..."
                  value={customText}
                  onChange={(e) => onCustomTextChange(e.target.value)}
                  disabled={disabled}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function QuestionDisplay({ toolInput, timestamp, onSendResponse, isAgentRunning, responded }: QuestionDisplayProps) {
  const questions = toolInput.questions || [];

  // State for each question's selections
  const [selections, setSelections] = useState<Map<number, Set<number>>>(new Map());
  const [customTexts, setCustomTexts] = useState<Map<number, string>>(new Map());
  const [otherSelected, setOtherSelected] = useState<Set<number>>(new Set());
  const [hasResponded, setHasResponded] = useState(responded || false);

  const handleOptionSelect = useCallback((questionIndex: number, optIndex: number, multiSelect: boolean) => {
    setSelections(prev => {
      const newSelections = new Map(prev);
      const current = newSelections.get(questionIndex) || new Set();

      if (multiSelect) {
        // Toggle selection for multi-select
        const newSet = new Set(current);
        if (newSet.has(optIndex)) {
          newSet.delete(optIndex);
        } else {
          newSet.add(optIndex);
        }
        newSelections.set(questionIndex, newSet);
      } else {
        // Single select - replace selection
        newSelections.set(questionIndex, new Set([optIndex]));
        // Deselect "other" when selecting a predefined option
        setOtherSelected(prev => {
          const newSet = new Set(prev);
          newSet.delete(questionIndex);
          return newSet;
        });
      }

      return newSelections;
    });
  }, []);

  const handleCustomTextChange = useCallback((questionIndex: number, text: string) => {
    setCustomTexts(prev => {
      const newTexts = new Map(prev);
      newTexts.set(questionIndex, text);
      return newTexts;
    });
  }, []);

  const handleOtherSelect = useCallback((questionIndex: number, multiSelect: boolean) => {
    setOtherSelected(prev => {
      const newSet = new Set(prev);
      if (newSet.has(questionIndex)) {
        newSet.delete(questionIndex);
      } else {
        newSet.add(questionIndex);
        // For single-select, clear option selections when choosing "other"
        if (!multiSelect) {
          setSelections(prevSel => {
            const newSelections = new Map(prevSel);
            newSelections.delete(questionIndex);
            return newSelections;
          });
        }
      }
      return newSet;
    });
  }, []);

  const handleSendResponse = useCallback(() => {
    if (!onSendResponse || hasResponded) return;

    // Build response string based on selections
    const responses: string[] = [];

    questions.forEach((question, qIndex) => {
      const selected = selections.get(qIndex) || new Set();
      const isOther = otherSelected.has(qIndex);
      const customText = customTexts.get(qIndex) || '';

      if (isOther && customText.trim()) {
        // Custom response
        responses.push(customText.trim());
      } else if (selected.size > 0) {
        // Selected options - use 1-based index for user-friendly display
        const selectedIndices = Array.from(selected).map(i => i + 1);
        if (question.multiSelect) {
          responses.push(selectedIndices.join(','));
        } else {
          responses.push(String(selectedIndices[0]));
        }
      }
    });

    if (responses.length > 0) {
      // Send the response (join multiple question responses with newline)
      onSendResponse(responses.join('\n'));
      setHasResponded(true);
    }
  }, [onSendResponse, questions, selections, otherSelected, customTexts, hasResponded]);

  // Check if we have at least one response ready
  const hasAnyResponse = questions.some((_, qIndex) => {
    const selected = selections.get(qIndex) || new Set();
    const isOther = otherSelected.has(qIndex);
    const customText = customTexts.get(qIndex) || '';
    return selected.size > 0 || (isOther && customText.trim());
  });

  const canRespond = isAgentRunning && !hasResponded && hasAnyResponse;

  return (
    <div className="py-2 pl-11">
      <div className="rounded-lg border border-purple-500/30 bg-purple-500/5 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 bg-purple-500/10 border-b border-purple-500/20">
          <HelpCircle className="w-4 h-4 text-purple-400" />
          <span className="font-medium text-purple-400">
            Question{questions.length > 1 ? 's' : ''} for User
          </span>
          <span className="text-xs text-gray-500">({questions.length})</span>
          {timestamp && (
            <span className="text-[10px] text-gray-600 font-mono ml-auto">{timestamp}</span>
          )}
        </div>

        {/* Questions */}
        <div className="p-3 space-y-3">
          {questions.map((question, index) => (
            <QuestionCard
              key={index}
              question={question}
              questionIndex={index}
              selectedOptions={selections.get(index) || new Set()}
              customText={customTexts.get(index) || ''}
              onOptionSelect={(optIndex) => handleOptionSelect(index, optIndex, question.multiSelect || false)}
              onCustomTextChange={(text) => handleCustomTextChange(index, text)}
              isOtherSelected={otherSelected.has(index)}
              onOtherSelect={() => handleOtherSelect(index, question.multiSelect || false)}
              disabled={hasResponded}
            />
          ))}
        </div>

        {/* Response action */}
        {onSendResponse && isAgentRunning && !hasResponded && (
          <div className="px-4 py-3 bg-purple-500/10 border-t border-purple-500/20">
            <button
              className={`w-full flex items-center justify-center gap-2 px-4 py-2 rounded font-medium transition-colors ${
                canRespond
                  ? 'bg-purple-600 hover:bg-purple-700 text-white'
                  : 'bg-gray-700 text-gray-400 cursor-not-allowed'
              }`}
              onClick={handleSendResponse}
              disabled={!canRespond}
            >
              <Send className="w-4 h-4" />
              Send Response
            </button>
          </div>
        )}

        {/* Status indicator */}
        {hasResponded ? (
          <div className="px-4 py-2 bg-green-500/10 border-t border-green-500/20">
            <span className="text-xs text-green-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              Response sent
            </span>
          </div>
        ) : !isAgentRunning ? (
          <div className="px-4 py-2 bg-gray-500/10 border-t border-gray-500/20">
            <span className="text-xs text-gray-400">
              Agent not running - cannot respond
            </span>
          </div>
        ) : !onSendResponse ? (
          <div className="px-4 py-2 bg-purple-500/10 border-t border-purple-500/20">
            <span className="text-xs text-purple-400">
              Select an option to respond
            </span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default QuestionDisplay;
