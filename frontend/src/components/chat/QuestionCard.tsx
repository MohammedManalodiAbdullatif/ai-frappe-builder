import React, { useState, useMemo } from 'react';
import { QuestionSpec, DiscoveryPhase } from '../../types';
import { Check, CornerDownRight } from 'lucide-react';

export interface QuestionCardProps {
  question: QuestionSpec;
  onAnswer: (answer: string) => void;
  answered?: boolean;
  answerText?: string | null;
  disabled?: boolean;
  onFocusComposer?: () => void;
}

const PHASE_LABELS: Record<DiscoveryPhase, string> = {
  basics: 'Basics',
  domain: 'About your business',
  confirm: 'Confirm',
};

interface NormalizedOption {
  value: string;
  label: string;
  description: string | null;
}

export const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  onAnswer,
  answered = false,
  answerText = null,
  disabled = false,
  onFocusComposer,
}) => {
  const [selectedMulti, setSelectedMulti] = useState<string[]>([]);

  const handleFocusComposer = () => {
    if (onFocusComposer) {
      onFocusComposer();
    } else {
      const composerEl = document.querySelector('textarea[data-composer], input[data-composer]') as HTMLElement | null;
      composerEl?.focus();
    }
  };

  // Safe normalized options array handling objects, strings, nulls
  const normalizedOptions: NormalizedOption[] = useMemo(() => {
    if (!question || !Array.isArray(question.options)) return [];
    return question.options
      .filter((opt: any) => opt !== null && opt !== undefined)
      .map((opt: any) => {
        if (typeof opt === 'string') {
          return { value: opt, label: opt, description: null };
        }
        return {
          value: String(opt.value || opt.label || ''),
          label: String(opt.label || opt.value || ''),
          description: opt.description ? String(opt.description) : null,
        };
      });
  }, [question?.options]);

  const questionText = question?.text || '';
  const questionHelp = question?.help || null;
  const phaseLabel = (question?.phase && PHASE_LABELS[question.phase]) || 'Discovery';

  // Collapsed state once answered
  if (answered || answerText) {
    return (
      <div
        className="mt-2 py-1.5 px-3 rounded-card bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--muted)] flex items-center gap-1.5 transition-all duration-200 motion-reduce:transition-none"
        data-testid="question-card-collapsed"
      >
        <Check className="w-3.5 h-3.5 text-[var(--accent)] flex-shrink-0" strokeWidth={2} />
        <span className="font-medium text-[var(--text)]">{questionText || 'Answered'}</span>
        <span className="text-[var(--muted)]">—</span>
        <span className="text-[var(--muted)] truncate">{answerText || 'Answered'}</span>
      </div>
    );
  }

  const handleToggleMulti = (val: string) => {
    setSelectedMulti((prev) =>
      prev.includes(val) ? prev.filter((item) => item !== val) : [...prev, val]
    );
  };

  const handleMultiSubmit = () => {
    if (selectedMulti.length === 0) return;
    const selectedLabels = normalizedOptions
      .filter((opt) => selectedMulti.includes(opt.value))
      .map((opt) => opt.label);
    onAnswer(selectedLabels.join(', '));
  };

  return (
    <div
      className="mt-3 p-4 rounded-card bg-[var(--surface)] border border-[var(--border)] flex flex-col gap-3 transition-all duration-200 motion-reduce:transition-none"
      data-testid="question-card"
    >
      {/* Header with Phase Chip */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <h4 className="text-[15px] font-semibold text-[var(--text)] leading-snug">
            {questionText}
          </h4>
          {questionHelp && (
            <p className="text-xs text-[var(--muted)] leading-relaxed">{questionHelp}</p>
          )}
        </div>
        <span className="flex-shrink-0 px-2 py-0.5 rounded-pill text-[11px] font-medium bg-[var(--bg)] border border-[var(--border)] text-[var(--muted)]">
          {phaseLabel}
        </span>
      </div>

      {/* Input Mode: Single Select */}
      {question?.input === 'single' && (
        <div className="flex flex-col gap-1.5 pt-1">
          {normalizedOptions.map((opt) => (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => onAnswer(opt.label)}
              className="w-full flex flex-col items-start px-3.5 py-2.5 rounded-card bg-[var(--bg)] hover:bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] text-left transition-colors group disabled:opacity-50"
            >
              <span className="text-sm font-medium text-[var(--text)] group-hover:text-[var(--accent)] transition-colors">
                {opt.label}
              </span>
              {opt.description && (
                <span className="text-xs text-[var(--muted)] mt-0.5 leading-normal">
                  {opt.description}
                </span>
              )}
            </button>
          ))}

          {question.allow_custom && (
            <button
              type="button"
              disabled={disabled}
              onClick={handleFocusComposer}
              className="w-full flex items-center justify-between px-3.5 py-2 rounded-card bg-[var(--bg)] hover:bg-[var(--surface)] border border-dashed border-[var(--border)] hover:border-[var(--accent)] text-left text-xs text-[var(--muted)] hover:text-[var(--accent)] transition-colors disabled:opacity-50"
            >
              <span>Something else…</span>
              <CornerDownRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {/* Input Mode: Multi Select */}
      {question?.input === 'multi' && (
        <div className="flex flex-col gap-2 pt-1">
          <div className="flex flex-col gap-1.5">
            {normalizedOptions.map((opt) => {
              const checked = selectedMulti.includes(opt.value);
              return (
                <div
                  key={opt.value}
                  className={`w-full flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-card border transition-colors ${
                    checked
                      ? 'bg-[var(--surface)] border-[var(--accent)] text-[var(--text)] ring-1 ring-[var(--accent)]'
                      : 'bg-[var(--bg)] border-[var(--border)] text-[var(--text)] hover:border-[var(--muted)]'
                  } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <label className="flex items-start gap-3 flex-1 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      disabled={disabled}
                      checked={checked}
                      onChange={() => handleToggleMulti(opt.value)}
                      className="mt-0.5 rounded border-[var(--border)] text-[var(--accent)] focus:ring-[var(--accent)]"
                    />
                    <div className="flex flex-col text-left">
                      <span className="text-sm font-medium">{opt.label}</span>
                      {opt.description && (
                        <span className="text-xs text-[var(--muted)] mt-0.5 leading-normal">
                          {opt.description}
                        </span>
                      )}
                    </div>
                  </label>

                  {/* Quick Direct Single-Click Submission */}
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onAnswer(opt.label);
                    }}
                    className="px-2.5 py-1 rounded bg-[var(--surface)] hover:bg-[var(--surface-hover)] border border-[var(--border)] hover:border-[var(--accent)] text-xs text-[var(--muted)] hover:text-[var(--accent)] transition-colors flex items-center gap-1 flex-shrink-0"
                    title={`Submit with only ${opt.label}`}
                  >
                    <span>Select only this</span>
                    <CornerDownRight className="w-3 h-3" />
                  </button>
                </div>
              );
            })}

            {question.allow_custom && (
              <button
                type="button"
                disabled={disabled}
                onClick={handleFocusComposer}
                className="w-full flex items-center justify-between px-3.5 py-2 rounded-card bg-[var(--bg)] hover:bg-[var(--surface)] border border-dashed border-[var(--border)] hover:border-[var(--accent)] text-left text-xs text-[var(--muted)] hover:text-[var(--accent)] transition-colors disabled:opacity-50"
              >
                <span>Something else…</span>
                <CornerDownRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="pt-2 flex flex-col gap-1.5">
            <button
              type="button"
              disabled={disabled || selectedMulti.length === 0}
              onClick={handleMultiSubmit}
              className={`w-full py-2.5 px-4 rounded-card text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                selectedMulti.length > 0
                  ? 'bg-[var(--accent)] hover:opacity-90 text-white shadow cursor-pointer'
                  : 'bg-[var(--surface)] border border-[var(--border)] text-[var(--muted)] opacity-50 cursor-not-allowed'
              }`}
            >
              <span>Continue</span>
              {selectedMulti.length > 0 && (
                <span className="opacity-90 font-medium">({selectedMulti.length} selected)</span>
              )}
              <CornerDownRight className="w-3.5 h-3.5" />
            </button>
            {selectedMulti.length === 0 && (
              <p className="text-[11px] text-[var(--muted)] text-center">
                Select checkboxes above and click Continue, or click &quot;Select only this&quot; on any role
              </p>
            )}
          </div>
        </div>
      )}

      {/* Input Mode: Yes/No */}
      {question?.input === 'yesno' && (
        <div className="flex items-center gap-2.5 pt-1">
          {normalizedOptions.length > 0 ? (
            normalizedOptions.map((opt) => (
              <button
                key={opt.value}
                type="button"
                disabled={disabled}
                onClick={() => onAnswer(opt.label)}
                className="flex-1 py-2 px-3 rounded-card bg-[var(--bg)] hover:bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] text-sm font-medium text-[var(--text)] text-center transition-colors disabled:opacity-50"
              >
                {opt.label}
              </button>
            ))
          ) : (
            <>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onAnswer('Yes')}
                className="flex-1 py-2 px-3 rounded-card bg-[var(--bg)] hover:bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] text-sm font-medium text-[var(--text)] text-center transition-colors disabled:opacity-50"
              >
                Yes
              </button>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onAnswer('No')}
                className="flex-1 py-2 px-3 rounded-card bg-[var(--bg)] hover:bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] text-sm font-medium text-[var(--text)] text-center transition-colors disabled:opacity-50"
              >
                No
              </button>
            </>
          )}
        </div>
      )}

      {/* Input Mode: Free Text or Fallback */}
      {(!question?.input || question.input === 'text') && (
        <div
          onClick={handleFocusComposer}
          className="pt-1 text-xs text-[var(--muted)] flex items-center gap-1.5 cursor-pointer hover:text-[var(--accent)] transition-colors"
        >
          <CornerDownRight className="w-3.5 h-3.5" />
          <span>Type your answer below</span>
        </div>
      )}
    </div>
  );
};
