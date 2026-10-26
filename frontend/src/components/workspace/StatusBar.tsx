import React, { useState } from 'react';
import { Download, Zap, Loader2, ExternalLink } from 'lucide-react';
import { ValidationReport, PipelineStage } from '../../types';

interface StatusBarProps {
  sessionId?: string | null;
  stage: PipelineStage;
  validation?: ValidationReport | null;
  qaReport?: {
    passed?: boolean;
    execution_mode?: string;
    failed_tests?: number;
    total_tests?: number;
  } | null;
  onApplyToFrappe?: () => void;
  isApplying?: boolean;
  applyResult?: any;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  sessionId,
  stage,
  validation,
  qaReport,
  onApplyToFrappe,
  isApplying = false,
  applyResult,
}) => {
  const [downloading, setDownloading] = useState(false);
  const [showAuditPopover, setShowAuditPopover] = useState(false);

  const handleDownload = () => {
    if (!sessionId) return;
    setDownloading(true);
    window.location.href = `http://localhost:8000/api/v1/export/${sessionId}/download`;
    setTimeout(() => setDownloading(false), 2000);
  };

  const isReady = stage === 'done';
  const hasValidationRun = !!validation;
  const errors = validation?.errors ?? [];
  const errorsCount = errors.length;

  // Group errors by category
  const wfErrors = errors.filter(
    (e) => e.includes('[WF') || e.toLowerCase().includes('workflow')
  );
  const permErrors = errors.filter(
    (e) => !wfErrors.includes(e) && e.toLowerCase().includes('permission')
  );
  const dtErrors = errors.filter(
    (e) => !wfErrors.includes(e) && !permErrors.includes(e)
  );

  // Bench QA rendering logic
  const renderBenchStatus = () => {
    if (qaReport) {
      if (qaReport.execution_mode === 'static_only') {
        return (
          <span className="flex items-center gap-1 text-[var(--muted)] font-mono">
            static-only
          </span>
        );
      }
      if (qaReport.passed) {
        return (
          <span className="flex items-center gap-1 text-[var(--ok)] font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--ok)]" />
            Passed
          </span>
        );
      }
      return (
        <span className="flex items-center gap-1 text-[var(--err)] font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--err)]" />
          Failed
        </span>
      );
    }

    if (isReady) {
      // Default fallback when Docker is unavailable in environment
      return (
        <span className="flex items-center gap-1 text-[var(--muted)] font-mono">
          static-only
        </span>
      );
    }

    return <span className="text-[var(--muted)] font-mono">—</span>;
  };

  return (
    <div className="flex items-center justify-between h-12 border-t border-[var(--border)] px-4 bg-[var(--surface)] text-xs select-none relative">
      {/* Audit & Bench QA Results */}
      <div className="flex items-center gap-4 text-muted">
        {/* Audit Result with Grouped Hover Popover */}
        <div
          className="relative flex items-center gap-1.5 cursor-pointer"
          onMouseEnter={() => setShowAuditPopover(true)}
          onMouseLeave={() => setShowAuditPopover(false)}
        >
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

          {/* Grouped Audit Popover */}
          {showAuditPopover && hasValidationRun && errorsCount > 0 && (
            <div className="absolute bottom-full left-0 mb-2 w-64 p-3 bg-[var(--surface)] border border-[var(--border)] rounded-card shadow-lg z-50 text-xs">
              <div className="font-semibold text-[var(--text)] mb-2 border-b border-[var(--border)] pb-1">
                Audit Errors Breakdown
              </div>
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between items-center text-[var(--text)]">
                  <span>Workflows:</span>
                  <span className={wfErrors.length > 0 ? 'text-[var(--err)] font-medium' : 'text-[var(--muted)]'}>
                    {wfErrors.length} error{wfErrors.length === 1 ? '' : 's'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-[var(--text)]">
                  <span>Permissions:</span>
                  <span className={permErrors.length > 0 ? 'text-[var(--err)] font-medium' : 'text-[var(--muted)]'}>
                    {permErrors.length} error{permErrors.length === 1 ? '' : 's'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-[var(--text)]">
                  <span>DocTypes:</span>
                  <span className={dtErrors.length > 0 ? 'text-[var(--err)] font-medium' : 'text-[var(--muted)]'}>
                    {dtErrors.length} error{dtErrors.length === 1 ? '' : 's'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Bench QA Result */}
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-[var(--muted)]">Bench QA:</span>
          {renderBenchStatus()}
        </div>
      </div>

      {/* Right Action Buttons */}
      <div className="flex items-center gap-2">
        {onApplyToFrappe && (
          <button
            onClick={onApplyToFrappe}
            disabled={!sessionId || isApplying}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--surface)] border border-[var(--accent)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-white disabled:opacity-40 disabled:cursor-not-allowed rounded-card text-xs font-medium transition-colors"
            title="Push DocTypes and Workflows directly to live Frappe Bench"
          >
            {isApplying ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Syncing to Bench...</span>
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5" />
                <span>Sync to Frappe</span>
              </>
            )}
          </button>
        )}

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
    </div>
  );
};
