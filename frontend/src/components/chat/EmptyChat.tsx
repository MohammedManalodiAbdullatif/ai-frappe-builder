import React from 'react';
import { ArrowUpRight } from 'lucide-react';

interface EmptyChatProps {
  onSelectPrompt: (prompt: string) => void;
}

const EXAMPLE_PROMPTS = [
  'Vehicle rental business',
  'Clinic appointments',
  'Custom HR module',
  'B2B wholesale distribution',
];

export const EmptyChat: React.FC<EmptyChatProps> = ({ onSelectPrompt }) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center select-none">
      <div className="max-w-md w-full flex flex-col items-center gap-6">
        <h1 className="text-xl font-semibold text-[var(--text)]">
          What are you building?
        </h1>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full">
          {EXAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onSelectPrompt(prompt)}
              className="flex items-center justify-between p-3.5 text-left bg-[var(--surface)] hover:border-[var(--accent)] border border-[var(--border)] rounded-card text-sm text-[var(--text)] transition-colors group"
            >
              <span>{prompt}</span>
              <ArrowUpRight className="w-4 h-4 text-[var(--muted)] group-hover:text-[var(--accent)] transition-colors" strokeWidth={1.5} />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
