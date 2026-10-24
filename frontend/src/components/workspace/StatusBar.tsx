import React, { useState } from 'react';
import { Download, AlertCircle, CheckCircle, Terminal } from 'lucide-react';
import { ValidationReport, PipelineStage } from '../../types';

interface StatusBarProps {
  sessionId?: string | null;
  stage: PipelineStage;
  validation?: ValidationReport | null;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  sessionId,
  stage,
  validation,
}) => {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = () => {
    if (!sessionId) return;
    setDownloading(true);
    window.location.href = `http://localhost:8000/api/v1/export/${sessionId}/download`;
    setTimeout(() => setDownloading(false), 2000);
  };

  const isReady = stage === 'done';
  const hasValidationRun = !!validation;
  const errorsCount = validation?.errors?.length ?? 0;
  const warningsCount = validation?.warnings?.length ?? 0;

  return (
    <div className="flex items-center justify-between h-12 border-t border-[var(--border)] px-4 bg-[var(--surface)] text-xs select-none">
      {/* Audit & Bench QA Results */}
      <div className="flex items-center gap-4 text-muted">
        {/* Audit Result */}
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-[var(--muted)]">Audit:</span>
          {hasValidationRun ? (
            errorsCount === 0 ? (
              <span className="flex items-center gap-1 text-[var(--ok)] font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--ok)]" />
                Valid
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[var(--err)] font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--err)]" />
                {errorsCount} error{errorsCount > 1 ? 's' : ''}
              </span>
            )
          ) : (
            <span className="text-[var(--muted)] font-mono">—</span>
          )}
        </div>

        {/* Bench QA Result */}
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-[var(--muted)]">Bench:</span>
          {isReady ? (
            <span className="flex items-center gap-1 text-[var(--ok)] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--ok)]" />
              Passed
            </span>
          ) : (
            <span className="text-[var(--muted)] font-mono">Not run yet</span>
          )}
        </div>
      </div>

      {/* Download Zip Action */}
      <button
        onClick={handleDownload}
        disabled={!isReady || !sessionId || downloading}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--accent)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-card text-xs font-medium transition-opacity"
      >
        <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
        <span>{downloading ? 'Exporting...' : 'Download .zip'}</span>
      </button>
    </div>
  );
};
