import React from 'react';
import { PipelineStage } from '../../types';

interface StageStepperProps {
  currentStage: PipelineStage;
  substate?: string | null;
  failedStage?: string | null;
  coverage?: { basics: number; domain: number } | null;
}

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: 'discovery', label: 'Discovery' },
  { key: 'drafting', label: 'Drafting' },
  { key: 'validating', label: 'Validating' },
  { key: 'healing', label: 'Healing' },
  { key: 'done', label: 'Ready' },
];

export const StageStepper: React.FC<StageStepperProps> = ({
  currentStage,
  substate,
  failedStage,
  coverage,
}) => {
  const isFailed = currentStage === 'failed';

  const getStageIdx = (stage: PipelineStage): number => {
    if (stage === 'failed') {
      if (failedStage) {
        const found = STAGES.findIndex((s) => s.key === failedStage.toLowerCase());
        if (found !== -1) return found;
      }
      return 3; // Default to Healing
    }
    const idx = STAGES.findIndex((s) => s.key === stage);
    if (idx !== -1) return idx;
    if (stage === 'scripting' || stage === 'reporting') return 1; // drafting
    if (stage === 'exporting' || stage === 'testing') return 2; // validating
    return 0;
  };

  const activeIdx = getStageIdx(currentStage);

  // Discovery progress: basics first, then domain once basics is complete
  const discoveryProgress = coverage
    ? coverage.basics < 1
      ? coverage.basics
      : coverage.domain
    : 0;

  return (
    <div className="flex flex-col gap-1 select-none">
      <div className="flex items-center gap-4 text-xs">
        {STAGES.map((s, idx) => {
          const isCurrent = activeIdx === idx;
          const isCompleted = activeIdx > idx || currentStage === 'done';

          let dotClass = 'border border-[var(--border)] bg-transparent';
          let labelClass = 'text-[var(--muted)]/60';

          if (isCurrent) {
            if (isFailed) {
              dotClass = 'bg-[var(--err)] ring-2 ring-[var(--err)]/30';
              labelClass = 'text-[var(--err)] font-semibold';
            } else {
              dotClass = 'bg-[var(--accent)]';
              labelClass = 'text-[var(--text)] font-semibold';
            }
          } else if (isCompleted) {
            dotClass = 'bg-[var(--muted)]';
            labelClass = 'text-[var(--muted)]';
          }

          // Special thin progress ring on Discovery stage dot
          if (s.key === 'discovery' && isCurrent && !isFailed && discoveryProgress > 0) {
            const radius = 5.5;
            const circumference = 2 * Math.PI * radius;
            const offset = circumference * (1 - Math.min(1, Math.max(0, discoveryProgress)));

            return (
              <div key={s.key} className="flex items-center gap-1.5">
                <div className="relative w-3.5 h-3.5 flex items-center justify-center">
                  <svg className="w-3.5 h-3.5 transform -rotate-90">
                    <circle
                      cx="7"
                      cy="7"
                      r={radius}
                      stroke="var(--border)"
                      strokeWidth="1.2"
                      fill="transparent"
                    />
                    <circle
                      cx="7"
                      cy="7"
                      r={radius}
                      stroke="var(--accent)"
                      strokeWidth="1.2"
                      strokeDasharray={circumference}
                      strokeDashoffset={offset}
                      strokeLinecap="round"
                      fill="transparent"
                      className="transition-all duration-300"
                    />
                  </svg>
                  <span className="absolute w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                </div>
                <span className={`transition-colors ${labelClass}`}>{s.label}</span>
              </div>
            );
          }

          return (
            <div key={s.key} className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full transition-colors ${dotClass}`} />
              <span className={`transition-colors ${labelClass}`}>{s.label}</span>
            </div>
          );
        })}
      </div>

      {/* Substate text display (Healing round info or Failed reason) */}
      {substate && (
        <span
          className={`text-[11px] font-mono transition-colors ${
            isFailed ? 'text-[var(--err)]' : 'text-[var(--muted)]'
          }`}
        >
          {substate}
        </span>
      )}
    </div>
  );
};
