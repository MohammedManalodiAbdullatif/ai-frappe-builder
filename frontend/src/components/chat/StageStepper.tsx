import React from 'react';
import { PipelineStage } from '../../types';

interface StageStepperProps {
  currentStage: PipelineStage;
}

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: 'discovery', label: 'Discovery' },
  { key: 'drafting', label: 'Drafting' },
  { key: 'validating', label: 'Validating' },
  { key: 'healing', label: 'Healing' },
  { key: 'done', label: 'Ready' },
];

export const StageStepper: React.FC<StageStepperProps> = ({ currentStage }) => {
  const getStageIdx = (stage: PipelineStage): number => {
    const idx = STAGES.findIndex((s) => s.key === stage);
    if (idx !== -1) return idx;
    if (stage === 'scripting' || stage === 'reporting') return 1; // drafting
    if (stage === 'exporting' || stage === 'testing') return 2; // validating
    return 0;
  };

  const activeIdx = getStageIdx(currentStage);

  return (
    <div className="flex items-center gap-4 text-xs select-none">
      {STAGES.map((s, idx) => {
        const isCurrent = activeIdx === idx;
        const isCompleted = activeIdx > idx || currentStage === 'done';

        return (
          <div key={s.key} className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full transition-colors ${
                isCurrent
                  ? 'bg-[var(--accent)] ring-2 ring-[var(--accent)]/30'
                  : isCompleted
                  ? 'bg-[var(--muted)]'
                  : 'border border-[var(--border)] bg-transparent'
              }`}
            />
            <span
              className={`transition-colors ${
                isCurrent
                  ? 'text-[var(--text)] font-semibold'
                  : isCompleted
                  ? 'text-[var(--muted)]'
                  : 'text-[var(--muted)]/60'
              }`}
            >
              {s.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};
