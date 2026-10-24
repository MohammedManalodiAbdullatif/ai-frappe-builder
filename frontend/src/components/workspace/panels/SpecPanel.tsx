import React, { useState } from 'react';
import { Braces, Copy, Check } from 'lucide-react';
import { AppMetadata } from '../../../types';

interface SpecPanelProps {
  app: AppMetadata | null;
  specRaw: any;
}

export const SpecPanel: React.FC<SpecPanelProps> = ({ app, specRaw }) => {
  const [copied, setCopied] = useState(false);
  const specData = specRaw || (app ? { app } : null);

  const handleCopy = () => {
    if (!specData) return;
    navigator.clipboard.writeText(JSON.stringify(specData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!specData) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted">
        <Braces className="w-8 h-8 mb-2 text-[var(--muted)]/40" strokeWidth={1.5} />
        <p className="text-sm font-medium text-[var(--muted)]">
          No spec JSON yet — it appears after Discovery
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-4 gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-[var(--muted)]">
          Frappe AppSpec 2.0
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-[var(--text)] bg-[var(--surface)] hover:border-[var(--accent)] border border-[var(--border)] rounded-card transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-[var(--ok)]" />
              <span className="text-[var(--ok)]">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" strokeWidth={1.5} />
              <span>Copy JSON</span>
            </>
          )}
        </button>
      </div>

      <pre className="flex-1 p-3.5 bg-[var(--surface)] border border-[var(--border)] rounded-card text-xs font-mono text-[var(--text)] overflow-auto leading-relaxed">
        {JSON.stringify(specData, null, 2)}
      </pre>
    </div>
  );
};
