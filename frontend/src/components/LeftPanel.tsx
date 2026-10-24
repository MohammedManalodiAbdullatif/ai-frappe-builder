import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  CheckCircle2,
  HelpCircle,
  Tag,
  CircleDashed,
  Cpu,
} from 'lucide-react';
import { Message, PipelineStage, InterviewQuestion } from '../types';

interface LeftPanelProps {
  stage: PipelineStage;
  messages: Message[];
  activeQuestion?: InterviewQuestion | null;
  assumptions: string[];
  archetype?: string;
  isProcessing: boolean;
  onSendMessage: (text: string) => void;
}

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: 'discovery', label: 'Discovery' },
  { key: 'drafting', label: 'Drafting' },
  { key: 'validating', label: 'Validating' },
  { key: 'healing', label: 'Healing' },
  { key: 'done', label: 'Ready' },
];

export const LeftPanel: React.FC<LeftPanelProps> = ({
  stage,
  messages,
  activeQuestion,
  assumptions,
  archetype,
  isProcessing,
  onSendMessage,
}) => {
  const [inputText, setInputText] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof chatEndRef.current?.scrollIntoView === 'function') {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activeQuestion]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isProcessing) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleSelectOption = (value: string) => {
    if (isProcessing) return;
    onSendMessage(value);
  };

  const getStageIndex = (current: PipelineStage) => {
    const idx = STAGES.findIndex((s) => s.key === current);
    return idx >= 0 ? idx : 0;
  };

  const currentIdx = getStageIndex(stage);

  return (
    <div className="flex flex-col h-full bg-slate-900 border-r border-slate-800 w-80 lg:w-96 flex-shrink-0 select-none">
      {/* 1. Header & Stepper */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-10">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-sky-400" />
            <span className="font-semibold text-sm text-slate-100 tracking-tight">AI Frappe Assistant</span>
          </div>
          {archetype && (
            <span className="px-2 py-0.5 text-xs font-mono rounded-full bg-sky-950 text-sky-400 border border-sky-800/50">
              {archetype}
            </span>
          )}
        </div>

        {/* State Stepper */}
        <div className="flex items-center justify-between gap-1">
          {STAGES.map((s, idx) => {
            const isPassed = currentIdx > idx || stage === 'done';
            const isCurrent = stage === s.key;
            return (
              <div key={s.key} className="flex-1 flex flex-col items-center">
                <div
                  className={`h-1.5 w-full rounded-full transition-all ${
                    isPassed
                      ? 'bg-emerald-500'
                      : isCurrent
                      ? 'bg-sky-500 animate-pulse'
                      : 'bg-slate-800'
                  }`}
                />
                <span
                  className={`text-[10px] mt-1 font-medium transition-colors ${
                    isCurrent
                      ? 'text-sky-400 font-bold'
                      : isPassed
                      ? 'text-emerald-400'
                      : 'text-slate-500'
                  }`}
                >
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Chat Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-sm">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <div
              className={`max-w-[88%] rounded-xl px-3.5 py-2.5 leading-relaxed text-sm ${
                msg.role === 'user'
                  ? 'bg-sky-600 text-white rounded-br-none shadow-sm'
                  : 'bg-slate-800/90 text-slate-200 border border-slate-700/60 rounded-bl-none shadow-sm'
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
            </div>
            <span className="text-[10px] text-slate-500 mt-1 px-1">
              {msg.timestamp || 'just now'}
            </span>
          </div>
        ))}

        {/* Active Discovery Question Card */}
        {activeQuestion && (
          <div className="bg-slate-800/90 border border-sky-500/40 rounded-xl p-3.5 shadow-lg shadow-sky-950/20">
            <div className="flex items-start gap-2 mb-2">
              <HelpCircle className="w-4 h-4 text-sky-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-slate-100 leading-snug">
                  {activeQuestion.question}
                </p>
                {activeQuestion.reason && (
                  <p className="text-xs text-slate-400 mt-1">
                    {activeQuestion.reason}
                  </p>
                )}
              </div>
            </div>

            {/* Interactive Option Pills */}
            <div className="flex flex-col gap-1.5 mt-3">
              {activeQuestion.options.map((opt, i) => {
                const label = typeof opt === 'string' ? opt : opt.label;
                const value = typeof opt === 'string' ? opt : opt.value;
                const desc = typeof opt === 'object' ? opt.description : undefined;

                return (
                  <button
                    key={i}
                    onClick={() => handleSelectOption(value)}
                    disabled={isProcessing}
                    className="flex flex-col items-start px-3 py-2 text-left rounded-lg bg-slate-900/80 hover:bg-sky-900/30 border border-slate-700/70 hover:border-sky-500/60 transition-all text-xs text-slate-200 hover:text-white group"
                  >
                    <span className="font-semibold text-slate-200 group-hover:text-sky-300">
                      {label}
                    </span>
                    {desc && (
                      <span className="text-[11px] text-slate-400 mt-0.5">
                        {desc}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Assumptions Accumulated */}
        {assumptions.length > 0 && (
          <div className="pt-2">
            <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <Tag className="w-3.5 h-3.5" />
              <span>Assumptions Identified</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {assumptions.map((assump, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-slate-800/80 border border-slate-700 text-slate-300 text-xs rounded-md leading-tight"
                >
                  {assump}
                </span>
              ))}
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* 3. Input Footer */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-slate-800 bg-slate-900/90">
        <div className="relative flex items-center">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={
              isProcessing
                ? 'Synthesizing with AI agents...'
                : 'Describe your business or answer question...'
            }
            disabled={isProcessing}
            className="w-full pl-3.5 pr-10 py-2.5 bg-slate-800/90 border border-slate-700/80 focus:border-sky-500 focus:ring-1 focus:ring-sky-500 rounded-xl text-slate-100 text-xs placeholder:text-slate-500 outline-none transition"
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isProcessing}
            className="absolute right-2 p-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:hover:bg-sky-600 text-white transition shadow-sm"
          >
            {isProcessing ? (
              <CircleDashed className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
