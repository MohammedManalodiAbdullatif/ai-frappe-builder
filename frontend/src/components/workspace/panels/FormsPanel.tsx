import React, { useState, useEffect } from 'react';
import { FileText, RotateCcw, Shield, Clock } from 'lucide-react';
import { AppMetadata, DocTypeSpec, WorkflowTransition, WorkflowSpec } from '../../../types';

interface FormsPanelProps {
  app: AppMetadata | null;
}

interface AuditEntry {
  timestamp: string;
  fromState: string;
  action: string;
  toState: string;
  role: string;
  docStatus: number;
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

  const workflow: WorkflowSpec | undefined = (app.workflows || []).find(
    (w) => w.document_type === activeDocType.name
  );

  // Initial state determination
  const initialState = React.useMemo(() => {
    if (!workflow || !workflow.states || workflow.states.length === 0) return null;
    const incoming: Record<string, number> = {};
    workflow.states.forEach((s) => {
      incoming[s.state] = 0;
    });
    (workflow.transitions || []).forEach((t) => {
      if (incoming[t.next_state] !== undefined) {
        incoming[t.next_state] += 1;
      }
    });
    const zeroes = Object.keys(incoming).filter((k) => incoming[k] === 0);
    return zeroes.length > 0 ? zeroes[0] : workflow.states[0].state;
  }, [workflow]);

  // Workflow simulation state
  const [currentStateName, setCurrentStateName] = useState<string>('');
  const [currentRole, setCurrentRole] = useState<string>('');
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);

  const roles = app?.roles || [];

  // Reset workflow simulation when activeDocType changes
  useEffect(() => {
    if (workflow && initialState) {
      setCurrentStateName(initialState);
      const initObj = workflow.states.find((s) => s.state === initialState);
      const defaultRole = initObj?.allow_edit || roles[0] || 'System Manager';
      setCurrentRole(defaultRole);
      setAuditTrail([
        {
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          fromState: '—',
          action: 'Document Created',
          toState: initialState,
          role: defaultRole,
          docStatus: initObj?.doc_status ?? 0,
        },
      ]);
    } else {
      setCurrentStateName('');
      setCurrentRole(roles[0] || 'System Manager');
      setAuditTrail([]);
    }
  }, [activeDocType.name, workflow, initialState, roles]);

  const currentStateObj = workflow?.states.find((s) => s.state === currentStateName);
  const currentDocStatus = currentStateObj?.doc_status ?? 0;

  // Valid actions for current state and active role
  const availableTransitions: WorkflowTransition[] = (workflow?.transitions || []).filter(
    (t) => t.state === currentStateName && t.allowed === currentRole
  );

  const handleApplyTransition = (trans: WorkflowTransition) => {
    const nextStateObj = workflow?.states.find((s) => s.state === trans.next_state);
    const nextStatus = nextStateObj?.doc_status ?? 0;

    setCurrentStateName(trans.next_state);
    setAuditTrail((prev) => [
      ...prev,
      {
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        fromState: currentStateName,
        action: trans.action,
        toState: trans.next_state,
        role: currentRole,
        docStatus: nextStatus,
      },
    ]);
  };

  const handleReset = () => {
    if (workflow && initialState) {
      const initObj = workflow.states.find((s) => s.state === initialState);
      setCurrentStateName(initialState);
      setAuditTrail([
        {
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          fromState: '—',
          action: 'Reset to Initial',
          toState: initialState,
          role: currentRole,
          docStatus: initObj?.doc_status ?? 0,
        },
      ]);
    }
  };

  // State color badge
  const getStatePillStyle = (styleName?: string) => {
    if (styleName === 'Success') return 'bg-[var(--ok)]/15 text-[var(--ok)] border-[var(--ok)]/30';
    if (styleName === 'Warning') return 'bg-[var(--warn)]/15 text-[var(--warn)] border-[var(--warn)]/30';
    if (styleName === 'Danger') return 'bg-[var(--err)]/15 text-[var(--err)] border-[var(--err)]/30';
    return 'bg-[var(--accent)]/15 text-[var(--accent)] border-[var(--accent)]/30';
  };

  const isFormLocked = currentDocStatus >= 1;

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
      {/* Top Controls: DocType Picker */}
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
        {/* Form Header */}
        <div className="flex flex-col gap-3 pb-3 border-b border-[var(--border)]">
          <div className="flex items-center justify-between">
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

          {/* Workflow Simulation Bar (when DocType has workflow) */}
          {workflow && (
            <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-[var(--bg)] border border-[var(--border)] rounded-card">
              <div className="flex items-center gap-2">
                {/* Workflow State Pill */}
                <span
                  className={`px-2.5 py-1 border rounded-pill text-xs font-semibold ${getStatePillStyle(
                    currentStateObj?.style
                  )}`}
                >
                  {currentStateName || 'Draft'}
                </span>

                {/* Role Switcher */}
                <div className="flex items-center gap-1.5 pl-2 border-l border-[var(--border)]">
                  <Shield className="w-3.5 h-3.5 text-[var(--muted)]" strokeWidth={1.5} />
                  <select
                    value={currentRole}
                    onChange={(e) => setCurrentRole(e.target.value)}
                    className="px-2 py-1 bg-[var(--surface)] border border-[var(--border)] rounded-card text-xs text-[var(--text)] outline-none"
                  >
                    {roles.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Action Buttons & Reset */}
              <div className="flex items-center gap-1.5">
                {availableTransitions.map((t, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleApplyTransition(t)}
                    className="px-2.5 py-1 bg-[var(--accent)] hover:opacity-90 text-white rounded-card text-xs font-medium transition-opacity"
                  >
                    {t.action}
                  </button>
                ))}
                <button
                  onClick={handleReset}
                  className="flex items-center gap-1 px-2 py-1 bg-[var(--surface)] border border-[var(--border)] text-[var(--muted)] hover:text-[var(--text)] rounded-card text-xs transition-colors"
                  title="Reset to initial state"
                >
                  <RotateCcw className="w-3 h-3" strokeWidth={1.5} />
                  <span>Reset</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Fields Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {activeDocType.fields.map((field) => {
            const isDisabled = isFormLocked && !field.allow_on_submit;

            return (
              <div key={field.fieldname} className="flex flex-col gap-1">
                <label className="text-xs font-medium text-[var(--muted)] flex items-center justify-between">
                  <span className="flex items-center gap-1">
                    <span>{field.label || field.fieldname}</span>
                    {field.reqd && <span className="text-[var(--err)]">*</span>}
                  </span>
                  {field.allow_on_submit && isFormLocked && (
                    <span className="text-[9px] text-[var(--accent)] font-mono">allow on submit</span>
                  )}
                </label>

                {field.fieldtype === 'Check' ? (
                  <div className="flex items-center gap-2 h-8">
                    <input
                      type="checkbox"
                      disabled={isDisabled}
                      className="w-4 h-4 accent-[var(--accent)] rounded disabled:opacity-50"
                    />
                    <span className={`text-xs ${isDisabled ? 'text-[var(--muted)]' : 'text-[var(--text)]'}`}>
                      Enabled
                    </span>
                  </div>
                ) : field.fieldtype === 'Select' ? (
                  <select
                    disabled={isDisabled}
                    className="px-2.5 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded-card text-xs text-[var(--text)] disabled:opacity-50"
                  >
                    {(field.options || '')
                      .split('\n')
                      .filter(Boolean)
                      .map((opt, i) => (
                        <option key={i} value={opt}>
                          {opt}
                        </option>
                      ))}
                  </select>
                ) : field.fieldtype === 'Text' || field.fieldtype === 'Small Text' ? (
                  <textarea
                    disabled={isDisabled}
                    rows={2}
                    placeholder={`[${field.fieldtype}]`}
                    className="px-2.5 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded-card text-xs text-[var(--muted)] resize-none disabled:opacity-50"
                  />
                ) : (
                  <input
                    type="text"
                    disabled={isDisabled}
                    placeholder={`[${field.fieldtype}] ${field.options ? `→ ${field.options}` : ''}`}
                    className="px-2.5 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded-card text-xs text-[var(--muted)] disabled:opacity-50"
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Mini Audit Trail Card (when workflow is active) */}
        {workflow && auditTrail.length > 0 && (
          <div className="mt-2 pt-3 border-t border-[var(--border)] flex flex-col gap-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--text)]">
              <Clock className="w-3.5 h-3.5 text-[var(--muted)]" strokeWidth={1.5} />
              <span>Audit Trail (Workflow History)</span>
            </div>
            <div className="flex flex-col gap-1.5 max-h-36 overflow-y-auto">
              {auditTrail.map((entry, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between px-2.5 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded-card text-[11px] text-[var(--text)]"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--muted)] font-mono">{entry.timestamp}</span>
                    <span className="font-medium text-[var(--accent)]">{entry.action}</span>
                    <span className="text-[var(--muted)]">by</span>
                    <span className="font-medium">{entry.role}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[var(--muted)]">{entry.fromState}</span>
                    <span>→</span>
                    <span className="font-semibold text-[var(--ok)]">{entry.toState}</span>
                    <span className="text-[9px] text-[var(--muted)] font-mono">
                      (doc_status: {entry.docStatus})
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
