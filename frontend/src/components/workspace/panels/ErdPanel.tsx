import React from 'react';
import { Layers, Link as LinkIcon, Table } from 'lucide-react';
import { AppMetadata } from '../../../types';

interface ErdPanelProps {
  app: AppMetadata | null;
}

export const ErdPanel: React.FC<ErdPanelProps> = ({ app }) => {
  if (!app || !app.doctypes || app.doctypes.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted">
        <Layers className="w-8 h-8 mb-2 text-[var(--muted)]/40" strokeWidth={1.5} />
        <p className="text-sm font-medium text-[var(--muted)]">
          No data model yet — it appears after Discovery
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
      <div className="text-xs font-medium text-[var(--muted)] mb-1">
        DocTypes ({app.doctypes.length})
      </div>

      <div className="grid grid-cols-1 gap-2.5">
        {app.doctypes.map((dt) => (
          <div
            key={dt.name}
            className="p-3.5 bg-[var(--surface)] border border-[var(--border)] rounded-card flex flex-col gap-2"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-[var(--text)]">
                  {dt.name}
                </span>
                {dt.istable && (
                  <span className="px-2 py-0.5 rounded-pill bg-[var(--border)] text-[var(--muted)] text-[10px] font-medium">
                    Child Table
                  </span>
                )}
                {dt.is_submittable && (
                  <span className="px-2 py-0.5 rounded-pill bg-[var(--accent)]/10 text-[var(--accent)] text-[10px] font-medium">
                    Submittable
                  </span>
                )}
              </div>
              <span className="text-xs text-[var(--muted)]">
                {dt.fields.length} fields
              </span>
            </div>

            {/* Fields list */}
            <div className="grid grid-cols-2 gap-1.5 pt-1 border-t border-[var(--border)]">
              {dt.fields.slice(0, 6).map((f) => (
                <div key={f.fieldname} className="flex items-center gap-1.5 text-xs text-[var(--text)] truncate">
                  {f.fieldtype === 'Link' ? (
                    <LinkIcon className="w-3 h-3 text-[var(--accent)] flex-shrink-0" strokeWidth={1.5} />
                  ) : f.fieldtype === 'Table' ? (
                    <Table className="w-3 h-3 text-[var(--warn)] flex-shrink-0" strokeWidth={1.5} />
                  ) : (
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--muted)] flex-shrink-0" />
                  )}
                  <span className="truncate">{f.label || f.fieldname}</span>
                  <span className="text-[10px] text-[var(--muted)] font-mono">({f.fieldtype})</span>
                </div>
              ))}
              {dt.fields.length > 6 && (
                <div className="text-[10px] text-[var(--muted)] col-span-2 pt-0.5">
                  + {dt.fields.length - 6} more fields
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
