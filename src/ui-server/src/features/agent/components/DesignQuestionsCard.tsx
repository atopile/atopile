import { useState } from 'react';
import type { DesignQuestionsData } from '../state/types';

export function DesignQuestionsCard({
  data,
  onSubmit,
}: {
  data: DesignQuestionsData;
  onSubmit: (answers: string) => void;
}) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const total = data.questions.length;
  const question = data.questions[currentIndex];
  if (!question) return null;

  const currentAnswer = answers[question.id] ?? '';
  const answeredCount = Object.values(answers).filter((value) => value.trim().length > 0).length;

  const selectOption = (option: string) => {
    setAnswers((previous) => ({ ...previous, [question.id]: option }));
    if (currentIndex < total - 1) {
      setCurrentIndex((index) => index + 1);
    }
  };

  const handleSubmit = () => {
    const lines: string[] = [];
    if (data.context) {
      lines.push(`Re: ${data.context}`);
      lines.push('');
    }
    for (const item of data.questions) {
      const answer = (answers[item.id] ?? '').trim() || item.default || 'No preference';
      lines.push(`${item.id}: ${answer}`);
    }
    onSubmit(lines.join('\n'));
  };

  return (
    <div className="agent-design-questions">
      {data.context && (
        <div className="agent-dq-context">{data.context}</div>
      )}
      <div className="agent-dq-nav">
        <span className="agent-dq-counter">
          Question {currentIndex + 1} of {total}
        </span>
        <span className="agent-dq-answered">
          {answeredCount}/{total} answered
        </span>
      </div>
      <div className="agent-dq-question">{question.question}</div>
      {question.options && question.options.length > 0 && (
        <div className="agent-dq-options">
          {question.options.map((option) => (
            <button
              key={option}
              type="button"
              className={`agent-dq-option ${currentAnswer === option ? 'selected' : ''}`}
              onClick={() => selectOption(option)}
            >
              {option}
              {question.default === option && <span className="agent-dq-default-badge">default</span>}
            </button>
          ))}
        </div>
      )}
      <div className="agent-dq-text-row">
        <input
          type="text"
          className="agent-dq-text-input"
          placeholder={question.default ? `Default: ${question.default}` : 'Type your answer...'}
          value={currentAnswer}
          onChange={(event) => setAnswers((previous) => ({ ...previous, [question.id]: event.target.value }))}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              if (currentIndex < total - 1) {
                setCurrentIndex((index) => index + 1);
              }
            }
          }}
        />
      </div>
      <div className="agent-dq-actions">
        <button
          type="button"
          className="agent-dq-prev"
          disabled={currentIndex === 0}
          onClick={() => setCurrentIndex((index) => Math.max(0, index - 1))}
        >
          Previous
        </button>
        {currentIndex < total - 1 ? (
          <button
            type="button"
            className="agent-dq-next"
            onClick={() => setCurrentIndex((index) => index + 1)}
          >
            Next
          </button>
        ) : (
          <button
            type="button"
            className="agent-dq-submit"
            onClick={handleSubmit}
          >
            Submit answers
          </button>
        )}
      </div>
      {total > 1 && (
        <div className="agent-dq-dots">
          {data.questions.map((item, index) => (
            <button
              key={item.id}
              type="button"
              className={`agent-dq-dot ${index === currentIndex ? 'active' : ''} ${(answers[item.id] ?? '').trim() ? 'answered' : ''}`}
              onClick={() => setCurrentIndex(index)}
              title={`${item.id}: ${item.question.substring(0, 50)}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
