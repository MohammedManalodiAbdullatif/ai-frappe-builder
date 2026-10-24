import React, { useEffect } from 'react';
import { X, Sliders, Radio, Cpu, Layers } from 'lucide-react';
import { AppSettings } from '../../state/useSession';

interface SettingsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onUpdateSettings: (newSettings: Partial<AppSettings>) => void;
  sseConnected: boolean;
}

export const SettingsDrawer: React.FC<SettingsDrawerProps> = ({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  sseConnected,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div
        className="relative w-full max-w-md bg-[var(--surface)] border border-[var(--border)] rounded-card p-6 flex flex-col gap-6 shadow-none"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-heading"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-[var(--accent)]" strokeWidth={1.5} />
            <h2 id="settings-heading" className="text-base font-semibold text-[var(--text)]">
              Settings
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-card text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--border)]"
            aria-label="Close settings"
          >
            <X className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-col gap-4 text-sm">
          {/* Model Selector */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[var(--muted)]">
              LLM Model
            </label>
            <select
              value={settings.model}
              onChange={(e) => onUpdateSettings({ model: e.target.value })}
              className="px-3 py-2 bg-[var(--bg)] border border-[var(--border)] rounded-card text-sm text-[var(--text)] outline-none"
            >
              <option value="gemma4:31b">gemma4:31b (Ollama Cloud)</option>
              <option value="deepseek-v4.1-flash">deepseek-v4.1-flash</option>
              <option value="mistral-large-3:675b">mistral-large-3:675b</option>
              <option value="minimax-m3.1-flash">minimax-m3.1-flash</option>
            </select>
          </div>

          {/* Frappe Version */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[var(--muted)]">
              Target Frappe Version
            </label>
            <select
              value={settings.frappeVersion}
              onChange={(e) => onUpdateSettings({ frappeVersion: e.target.value })}
              className="px-3 py-2 bg-[var(--bg)] border border-[var(--border)] rounded-card text-sm text-[var(--text)] outline-none"
            >
              <option value="v15">Frappe v15 (Standard)</option>
              <option value="v14">Frappe v14 (Legacy)</option>
            </select>
          </div>

          {/* ERPNext Integration Toggle */}
          <div className="flex items-center justify-between pt-1">
            <div className="flex flex-col">
              <span className="text-sm font-medium text-[var(--text)]">
                Reuse ERPNext Core DocTypes
              </span>
              <span className="text-xs text-[var(--muted)]">
                Link existing Customer, Item, and Company
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings.erpnextRequired}
              onChange={(e) => onUpdateSettings({ erpnextRequired: e.target.checked })}
              className="w-4 h-4 accent-[var(--accent)] rounded cursor-pointer"
            />
          </div>

          {/* SSE Stream Status */}
          <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
            <div className="flex items-center gap-2 text-sm text-[var(--text)]">
              <Radio className="w-4 h-4 text-[var(--muted)]" strokeWidth={1.5} />
              <span>Real-time SSE Events</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs font-medium">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: sseConnected ? 'var(--ok)' : 'var(--muted)' }}
              />
              <span style={{ color: sseConnected ? 'var(--ok)' : 'var(--muted)' }}>
                {sseConnected ? 'Connected' : 'Offline'}
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-2 border-t border-[var(--border)] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[var(--accent)] hover:opacity-90 text-white rounded-card text-sm font-medium transition-opacity"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
