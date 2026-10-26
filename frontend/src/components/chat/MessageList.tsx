import React, { useRef, useEffect } from 'react';
import { Message } from './Message';
import { QuestionCard } from './QuestionCard';
import { Message as MessageType, InterviewQuestion, QuestionSpec } from '../../types';
import { Box } from 'lucide-react';

interface MessageListProps {
  messages: MessageType[];
  activeQuestion?: InterviewQuestion | null;
  onSelectOption: (option: string) => void;
  onRetryValidation?: () => void;
  isProcessing: boolean;
  isStreaming: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  activeQuestion,
  onSelectOption,
  onRetryValidation,
  isProcessing,
  isStreaming,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof scrollRef.current?.scrollIntoView === 'function') {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isStreaming, activeQuestion]);

  // Find the index of the latest assistant message that contains an active interview turn
  const latestAssistantTurnIdx = messages
    .map((m, idx) => ({ m, idx }))
    .filter(({ m }) => m.role === 'assistant' && Boolean(m.interview_turn?.question))
    .pop()?.idx;

  // Check if the latest assistant message has an embedded active question
  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === 'assistant');
  const latestAssistantHasQuestion = Boolean(lastAssistantMsg?.interview_turn?.question);

  // Fallback question spec when the latest message does not have an embedded question
  const fallbackQuestionSpec: QuestionSpec | null =
    !latestAssistantHasQuestion && activeQuestion
      ? {
          id: activeQuestion.id,
          phase: 'basics',
          text: activeQuestion.question,
          help: activeQuestion.reason || null,
          input: 'single',
          options: (activeQuestion.options || []).map((opt) =>
            typeof opt === 'string'
              ? { label: opt, value: opt }
              : { label: opt.label, value: opt.value, description: opt.description }
          ),
        }
      : null;

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-[760px] mx-auto flex flex-col gap-2">
        {messages.map((msg, index) => {
          const isLatestTurn = index === latestAssistantTurnIdx;
          return (
            <Message
              key={msg.id}
              message={msg}
              onRetryValidation={onRetryValidation}
              onAnswerQuestion={onSelectOption}
              isLatestTurn={isLatestTurn}
              isProcessing={isProcessing}
            />
          );
        })}

        {/* Fallback QuestionCard when activeQuestion is passed directly */}
        {fallbackQuestionSpec && (
          <QuestionCard
            question={fallbackQuestionSpec}
            onAnswer={onSelectOption}
            disabled={isProcessing}
          />
        )}

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

        <div ref={scrollRef} />
      </div>
    </div>
  );
};
