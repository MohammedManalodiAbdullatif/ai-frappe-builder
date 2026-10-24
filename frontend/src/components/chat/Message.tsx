import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Check, Box } from 'lucide-react';
import { Message as MessageType } from '../../types';

interface MessageProps {
  message: MessageType;
  isStreaming?: boolean;
}

export const Message: React.FC<MessageProps> = ({ message, isStreaming = false }) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end w-full py-1.5 group">
        <div className="relative max-w-[80%] px-4 py-2.5 bg-[var(--accent)] text-white rounded-card text-sm leading-relaxed">
          <div className="whitespace-pre-wrap">{message.content}</div>
          <button
            onClick={handleCopy}
            className="opacity-0 group-hover:opacity-100 transition-opacity absolute -left-8 top-2 p-1 text-[var(--muted)] hover:text-[var(--text)]"
            title="Copy message"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-[var(--ok)]" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 w-full py-3 group">
      {/* Assistant avatar */}
      <div className="w-6 h-6 rounded-card bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center flex-shrink-0 mt-0.5 text-[var(--accent)]">
        <Box className="w-3.5 h-3.5" strokeWidth={1.5} />
      </div>

      {/* Assistant message content row */}
      <div className="flex-1 overflow-hidden text-sm leading-relaxed text-[var(--text)]">
        <div className="prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-[var(--surface)] prose-pre:border prose-pre:border-[var(--border)] prose-pre:rounded-card">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Copy button */}
        <div className="mt-2 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-[var(--muted)] hover:text-[var(--text)] transition-colors py-0.5"
            title="Copy response"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-[var(--ok)]" />
                <span className="text-[var(--ok)]">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
