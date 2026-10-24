import React, { useState, useRef, useEffect } from 'react';
import { Message, Question } from '../types';
import { Send, HelpCircle, Sparkles, Loader2 } from 'lucide-react';

interface Props {
  messages: Message[];
  questions: Question[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  status: string;
}

export const ChatPane: React.FC<Props> = ({
  messages,
  questions,
  isLoading,
  onSendMessage,
  status,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, questions, isLoading]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSelectOption = (opt: string) => {
    setInput((prev) => (prev ? `${prev}, ${opt}` : opt));
  };

  return (
    <div className="left-pane">
      <div className="chat-messages">
        {messages.map((m) => (
          <div key={m.id} className={`message-wrapper ${m.role}`}>
            <div className="message-bubble">
              {m.content}
            </div>
            <span className="message-time">{m.timestamp}</span>
          </div>
        ))}

        {/* Discovery Questions Card */}
        {questions && questions.length > 0 && (
          <div className="questions-card">
            <h4>
              <HelpCircle size={16} /> Discovery Questions to clarify schema:
            </h4>
            {questions.map((q) => (
              <div key={q.id} className="question-item">
                <div className="question-text">{q.question}</div>
                {q.why_it_matters && (
                  <div className="question-why">Reason: {q.why_it_matters}</div>
                )}
                {q.options && q.options.length > 0 && (
                  <div className="question-options">
                    {q.options.map((opt, idx) => (
                      <span
                        key={idx}
                        className="option-badge"
                        onClick={() => handleSelectOption(opt)}
                      >
                        + {opt}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {isLoading && (
          <div className="message-wrapper assistant">
            <div className="message-bubble" style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#4f46e5' }}>
              <Loader2 className="animate-spin" size={16} />
              AI is reasoning & generating Frappe schema...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-bar">
        <form onSubmit={handleSubmit} className="input-row">
          <textarea
            className="chat-textarea"
            placeholder={
              status === 'needs_input'
                ? 'Answer the discovery questions above...'
                : 'Describe what business processes you want in Frappe...'
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={2}
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!input.trim() || isLoading}
            style={{ height: 44, padding: '0 16px' }}
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </form>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8' }}>
          <span>Press <strong>Enter</strong> to send, <strong>Shift+Enter</strong> for newline</span>
          <span>Status: <strong>{status}</strong></span>
        </div>
      </div>
    </div>
  );
};
