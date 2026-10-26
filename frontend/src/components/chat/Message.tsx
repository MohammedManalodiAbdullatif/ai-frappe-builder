import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Check, Box, RefreshCw } from 'lucide-react';
import { Message as MessageType } from '../../types';
import { QuestionCard } from './QuestionCard';

interface MessageProps {
  message: MessageType;
  isStreaming?: boolean;
  onRetryValidation?: () => void;
  onAnswerQuestion?: (answer: string) => void;
  isLatestTurn?: boolean;
  isProcessing?: boolean;
}

const CodeBlock = ({ children, className, ...props }: any) => {
  const [copied, setCopied] = useState(false);
  const codeText = String(children || '').replace(/\n$/, '');
  const isInline = !className && !codeText.includes('\n');

  if (isInline) {
    return (
      <code className="px-1.5 py-0.5 rounded bg-[var(--surface-hover)] font-mono text-xs" {...props}>
        {children}
      </code>
    );
  }

  const handleCopy = () => {
    if (codeText) {
      navigator.clipboard.writeText(codeText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="relative group/code my-2.5">
      <pre className="p-3.5 rounded-card bg-[var(--surface)] border border-[var(--border)] overflow-x-auto font-mono text-xs leading-relaxed">
        <code className={className} {...props}>
          {children}
        </code>
      </pre>
      <button
        onClick={handleCopy}
        className="opacity-0 group-hover/code:opacity-100 transition-opacity absolute right-2.5 top-2.5 p-1 rounded bg-[var(--bg)] border border-[var(--border)] text-[var(--muted)] hover:text-[var(--text)]"
        title="Copy code"
      >
        {copied ? <Check className="w-3.5 h-3.5 text-[var(--ok)]" /> : <Copy className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
};

export const Message: React.FC<MessageProps> = ({
  message,
  onRetryValidation,
  onAnswerQuestion,
  isLatestTurn = false,
  isProcessing = false,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message?.role === 'user';

  // Ensure content is always safely cast to string
  const contentStr =
    typeof message?.content === 'string'
      ? message.content
      : typeof message?.content === 'object'
      ? JSON.stringify(message.content)
      : String(message?.content || '');

  const handleCopyUser = () => {
    navigator.clipboard.writeText(contentStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end w-full py-1.5 group">
        <div className="relative max-w-[80%] px-4 py-2.5 bg-[var(--accent)] text-white rounded-card text-sm leading-relaxed">
          <div className="whitespace-pre-wrap">{contentStr}</div>
          <button
            onClick={handleCopyUser}
            className="opacity-0 group-hover:opacity-100 transition-opacity absolute -left-8 top-2 p-1 text-[var(--muted)] hover:text-[var(--text)]"
            title="Copy message"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-[var(--ok)]" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
    );
  }

  const turn = message?.interview_turn;

  return (
    <div className="flex items-start gap-3 w-full py-3" data-testid="assistant-message-row">
      {/* Small assistant avatar */}
      <div className="w-6 h-6 rounded-card bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center flex-shrink-0 mt-0.5 text-[var(--accent)]">
        <Box className="w-3.5 h-3.5" strokeWidth={1.5} />
      </div>

      {/* Assistant message content row */}
      <div className="flex-1 overflow-hidden text-sm leading-relaxed text-[var(--text)]">
        {turn ? (
          /* Interview Turn: Avatar + 'say' + QuestionCard inside same row */
          <div className="flex flex-col">
            <div className="text-sm leading-relaxed text-[var(--text)]">
              {turn.say || contentStr}
            </div>
            {turn.question && (
              <QuestionCard
                question={turn.question}
                onAnswer={(answer) => onAnswerQuestion && onAnswerQuestion(answer)}
                answered={Boolean(message?.answeredAnswer || !isLatestTurn)}
                answerText={message?.answeredAnswer}
                disabled={isProcessing}
              />
            )}
          </div>
        ) : (
          /* Normal assistant row with ReactMarkdown (no row-level copy button) */
          <div className="prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:p-0 prose-pre:bg-transparent">
            <ReactMarkdown components={{ code: CodeBlock }}>{contentStr}</ReactMarkdown>
          </div>
        )}

        {/* Retry validation button if message is a validation failure */}
        {(contentStr.includes('Retry validation') ||
          contentStr.includes('Unresolved Validation Errors')) &&
          onRetryValidation && (
            <div className="mt-3">
              <button
                onClick={onRetryValidation}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--surface)] hover:bg-[var(--border)] border border-[var(--border)] text-[var(--text)] rounded-card text-xs font-medium transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.5} />
                <span>Retry validation</span>
              </button>
            </div>
          )}
      </div>
    </div>
  );
};
