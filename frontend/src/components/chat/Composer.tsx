import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';

interface ComposerProps {
  onSend: (text: string) => void;
  disabled: boolean;
  isQuestionActive?: boolean;
}

export const Composer: React.FC<ComposerProps> = ({
  onSend,
  disabled,
  isQuestionActive = false,
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow textarea up to 6 lines (~144px)
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 144)}px`;
    }
  }, [text]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const placeholderText = isQuestionActive
    ? 'Or type your own answer…'
    : 'Ask a question or describe your app requirements...';

  return (
    <div className="w-full max-w-[760px] mx-auto px-4 pb-4">
      <div className="relative flex items-end bg-[var(--surface)] border border-[var(--border)] focus-within:border-[var(--accent)] rounded-card p-2 transition-colors">
        <textarea
          ref={textareaRef}
          data-composer="true"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholderText}
          rows={1}
          className="flex-1 bg-transparent text-sm text-[var(--text)] placeholder-[var(--muted)] resize-none outline-none max-h-36 px-2 py-1.5 leading-relaxed"
        />

        <button
          type="button"
          onClick={handleSend}
          disabled={!text.trim() || disabled}
          className="p-2 rounded-card bg-[var(--accent)] hover:opacity-90 disabled:opacity-30 text-white transition-opacity flex-shrink-0"
          aria-label="Send message"
        >
          <ArrowUp className="w-4 h-4" strokeWidth={2} />
        </button>
      </div>

      <div className="text-center mt-2 text-xs text-[var(--muted)]">
        Press Enter to send, Shift + Enter for a new line
      </div>
    </div>
  );
};
