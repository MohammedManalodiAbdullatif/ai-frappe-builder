import React from 'react';
import { GitBranch, ArrowRight } from 'lucide-react';
import { AppMetadata } from '../../../types';

interface WorkflowsPanelProps {
  app: AppMetadata | null;
}

export const WorkflowsPanel: React.FC<WorkflowsPanelProps> = ({ app }) => {
  if (!app || !app.workflows || app.workflows.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted">
        <GitBranch className="w-8 h-8 mb-2 text-[var(--muted)]/40" strokeWidth={1.5} />
        <p className="text-sm font-medium text-[var(--muted)]">
          No workflows yet — they appear after Drafting
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
      {app.workflows.map((wf) => (
        <div
          key={wf.name}
          className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-card flex flex-col gap-3"
        >
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
            <h3 className="text-sm font-semibold text-[var(--text)]">{wf.name}</h3>
            <span className="text-xs text-[var(--muted)]">DocType: {wf.document_type}</span>
          </div>

          {/* States */}
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-[var(--muted)]">States</span>
            <div className="flex flex-wrap gap-1.5">
              {wf.states.map((st) => (
                <span
                  key={st.state}
                  className="px-2.5 py-1 bg-[var(--bg)] border border-[var(--border)] rounded-pill text-xs text-[var(--text)]"
                >
                  {st.state}
                </span>
              ))}
            </div>
          </div>

          {/* Transitions */}
          {wf.transitions && wf.transitions.length > 0 && (
            <div className="flex flex-col gap-1.5 pt-2 border-t border-[var(--border)]">
              <span className="text-xs font-medium text-[var(--muted)]">Transitions</span>
              <div className="flex flex-col gap-1.5">
                {wf.transitions.map((tr, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between px-2.5 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded-card text-xs text-[var(--text)]"
                  >
                    <span className="font-medium">{tr.state}</span>
                    <div className="flex items-center gap-1.5 text-[var(--muted)]">
                      <span className="text-[var(--accent)] font-mono text-[11px]">{tr.action}</span>
                      <ArrowRight className="w-3 h-3" strokeWidth={1.5} />
                    </div>
                    <span className="font-medium text-[var(--ok)]">{tr.next_state}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
