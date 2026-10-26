import React, { useEffect, useState } from 'react';
import { X, Sliders, Radio, Cpu, Layers, Server, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { AppSettings } from '../../state/useSession';
import { api } from '../../api';

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
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionResult, setConnectionResult] = useState<any>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setConnectionResult(null);
    try {
      const res = await api.testFrappeConnection(
        settings.frappeUrl || 'http://crm.localhost:8015',
        settings.frappeApiKey || '992f21dbfdb7f47',
        settings.frappeApiSecret || 'acf9538d97bf2a6'
      );
      setConnectionResult(res);
    } catch (err: any) {
      setConnectionResult({ ok: false, error: err.message });
    } finally {
      setTestingConnection(false);
    }
  };

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

          {/* Live Frappe Site Integration */}
          <div className="flex flex-col gap-2 pt-2 border-t border-[var(--border)]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 font-medium text-xs text-[var(--text)]">
                <Server className="w-3.5 h-3.5 text-[var(--accent)]" />
                <span>Live Frappe Bench Site</span>
              </div>
              <button
                onClick={handleTestConnection}
                disabled={testingConnection}
                className="px-2 py-0.5 rounded text-[11px] font-medium bg-[var(--border)] text-[var(--text)] hover:bg-[var(--accent)] hover:text-white transition-colors flex items-center gap-1 disabled:opacity-50"
              >
                {testingConnection ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>Connecting...</span>
                  </>
                ) : (
                  <span>Test Connection</span>
                )}
              </button>
            </div>

            <div className="flex flex-col gap-1.5">
              <input
                type="text"
                placeholder="Frappe Site URL (e.g. http://crm.localhost:8015)"
                value={settings.frappeUrl || ''}
                onChange={(e) => onUpdateSettings({ frappeUrl: e.target.value })}
                className="w-full px-2.5 py-1.5 rounded-card border border-[var(--border)] bg-[var(--bg)] text-xs text-[var(--text)] font-mono outline-none"
              />
              <div className="grid grid-cols-2 gap-1.5">
                <input
                  type="password"
                  placeholder="API Key"
                  value={settings.frappeApiKey || ''}
                  onChange={(e) => onUpdateSettings({ frappeApiKey: e.target.value })}
                  className="w-full px-2.5 py-1.5 rounded-card border border-[var(--border)] bg-[var(--bg)] text-xs text-[var(--text)] font-mono outline-none"
                />
                <input
                  type="password"
                  placeholder="API Secret"
                  value={settings.frappeApiSecret || ''}
                  onChange={(e) => onUpdateSettings({ frappeApiSecret: e.target.value })}
                  className="w-full px-2.5 py-1.5 rounded-card border border-[var(--border)] bg-[var(--bg)] text-xs text-[var(--text)] font-mono outline-none"
                />
              </div>
            </div>

            {connectionResult && (
              <div
                className={`p-2 rounded-card text-[11px] flex items-center gap-1.5 ${
                  connectionResult.ok
                    ? 'bg-[var(--ok)]/10 text-[var(--ok)]'
                    : 'bg-[var(--err)]/10 text-[var(--err)]'
                }`}
              >
                {connectionResult.ok ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>
                      Live site connected! ({connectionResult.installed_apps.length} apps,{' '}
                      {connectionResult.doctypes_count} DocTypes)
                    </span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="truncate">{connectionResult.error}</span>
                  </>
                )}
              </div>
            )}
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
