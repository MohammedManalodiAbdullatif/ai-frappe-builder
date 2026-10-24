import React, { useState } from 'react';
import { FileText, Hash, Check } from 'lucide-react';
import { AppMetadata, DocTypeSpec } from '../../../types';

interface FormsPanelProps {
  app: AppMetadata | null;
}

export const FormsPanel: React.FC<FormsPanelProps> = ({ app }) => {
  const [selectedDocTypeName, setSelectedDocTypeName] = useState<string | null>(null);

  if (!app || !app.doctypes || app.doctypes.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted">
        <FileText className="w-8 h-8 mb-2 text-[var(--muted)]/40" strokeWidth={1.5} />
        <p className="text-sm font-medium text-[var(--muted)]">
          No form schemas yet — they appear after Drafting
        </p>
      </div>
    );
  }

  const activeDocType: DocTypeSpec =
    app.doctypes.find((d) => d.name === selectedDocTypeName) || app.doctypes[0];

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
      {/* DocType Picker */}
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-[var(--muted)]">Select DocType</label>
        <select
          value={activeDocType.name}
          onChange={(e) => setSelectedDocTypeName(e.target.value)}
          className="px-2.5 py-1.5 bg-[var(--surface)] border border-[var(--border)] rounded-card text-xs text-[var(--text)] outline-none"
        >
          {app.doctypes.map((dt) => (
            <option key={dt.name} value={dt.name}>
              {dt.name}
            </option>
          ))}
        </select>
      </div>

      {/* Simulated Form Desk Card */}
      <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-card flex flex-col gap-4">
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
          <div>
            <h3 className="text-sm font-semibold text-[var(--text)]">{activeDocType.name}</h3>
            <span className="text-xs text-[var(--muted)]">
              Module: {activeDocType.module} | Autoname: {activeDocType.autoname || 'Prompt/Series'}
            </span>
          </div>
          {activeDocType.is_submittable && (
            <span className="px-2 py-0.5 rounded-pill bg-[var(--accent)]/10 text-[var(--accent)] text-[10px] font-medium">
              Submittable
            </span>
          )}
        </div>

        {/* Fields Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {activeDocType.fields.map((field) => (
            <div key={field.fieldname} className="flex flex-col gap-1">
              <label className="text-xs font-medium text-[var(--muted)] flex items-center gap-1">
                <span>{field.label || field.fieldname}</span>
                {field.reqd && <span className="text-[var(--err)]">*</span>}
              </label>

              {field.fieldtype === 'Check' ? (
                <div className="flex items-center gap-2 h-8">
                  <input
                    type="checkbox"
                    disabled
                    className="w-4 h-4 accent-[var(--accent)] rounded"
                  />
                  <span className="text-xs text-[var(--text)]">Enabled</span>
                </div>
              ) : field.fieldtype === 'Select' ? (
                <select
                  disabled
                  className="px-2.5 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded-card text-xs text-[var(--text)]"
                >
                  <option>Select option...</option>
                </select>
              ) : field.fieldtype === 'Text' || field.fieldtype === 'Small Text' ? (
                <textarea
                  disabled
                  rows={2}
                  placeholder={`[${field.fieldtype}]`}
                  className="px-2.5 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded-card text-xs text-[var(--muted)] resize-none"
                />
              ) : (
                <input
                  type="text"
                  disabled
                  placeholder={`[${field.fieldtype}] ${field.options ? `→ ${field.options}` : ''}`}
                  className="px-2.5 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded-card text-xs text-[var(--muted)]"
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
