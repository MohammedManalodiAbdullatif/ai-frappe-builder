import React, { useRef, useEffect } from 'react';
import { Message } from './Message';
import { Message as MessageType, InterviewQuestion } from '../../types';
import { Box, HelpCircle } from 'lucide-react';

interface MessageListProps {
  messages: MessageType[];
  activeQuestion: InterviewQuestion | null;
  onSelectOption: (option: string) => void;
  isProcessing: boolean;
  isStreaming: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  activeQuestion,
  onSelectOption,
  isProcessing,
  isStreaming,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof scrollRef.current?.scrollIntoView === 'function') {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activeQuestion, isStreaming]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-[760px] mx-auto flex flex-col gap-2">
        {messages.map((msg) => (
          <Message key={msg.id} message={msg} />
        ))}

        {/* Streaming Typing Indicator */}
        {isStreaming && (
          <div className="flex items-center gap-3 py-2 text-[var(--muted)]">
            <div className="w-6 h-6 rounded-card bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center flex-shrink-0 text-[var(--accent)]">
              <Box className="w-3.5 h-3.5" strokeWidth={1.5} />
            </div>
            <div className="flex items-center gap-1.5 text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse delay-75" />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse delay-150" />
            </div>
          </div>
        )}

        {/* Questionnaire Dialogue Box */}
        {activeQuestion && (
          <div className="mt-4 p-4 rounded-card bg-[var(--surface)] border border-[var(--border)] flex flex-col gap-3">
            <div className="flex items-start gap-2.5">
              <HelpCircle className="w-4 h-4 text-[var(--accent)] flex-shrink-0 mt-0.5" strokeWidth={1.5} />
              <div className="flex flex-col gap-1">
                <span className="text-sm font-semibold text-[var(--text)]">
                  {activeQuestion.question}
                </span>
                {activeQuestion.reason && (
                  <span className="text-xs text-[var(--muted)]">
                    {activeQuestion.reason}
                  </span>
                )}
              </div>
            </div>

            {/* Clickable Option Pills / Cards */}
            <div className="grid grid-cols-1 gap-2 pt-1">
              {activeQuestion.options.map((opt, idx) => {
                const label = typeof opt === 'string' ? opt : opt.label;
                const value = typeof opt === 'string' ? opt : opt.value;
                const desc = typeof opt === 'object' ? opt.description : undefined;

                return (
                  <button
                    key={idx}
                    onClick={() => onSelectOption(value)}
                    disabled={isProcessing}
                    className="flex flex-col items-start px-3.5 py-2.5 rounded-card bg-[var(--bg)] hover:bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] text-left transition-colors group disabled:opacity-50"
                  >
                    <span className="text-sm font-medium text-[var(--text)] group-hover:text-[var(--accent)] transition-colors">
                      {label}
                    </span>
                    {desc && (
                      <span className="text-xs text-[var(--muted)] mt-0.5">
                        {desc}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div ref={scrollRef} />
      </div>
    </div>
  );
};
