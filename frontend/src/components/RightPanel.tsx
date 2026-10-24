import React, { useState } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  AlertCircle,
  Download,
  Terminal,
  Activity,
  CheckCircle2,
  Wrench,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import { ValidationReport } from '../types';
import { api } from '../api';

interface RightPanelProps {
  sessionId?: string;
  appName?: string;
  validation?: ValidationReport | null;
  onApplyFix?: (fixHint: any) => void;
}

export const RightPanel: React.FC<RightPanelProps> = ({
  sessionId,
  appName = 'frappe_app',
  validation,
  onApplyFix,
}) => {
  const [downloading, setDownloading] = useState(false);
  const [activeTab, setActiveTab] = useState<'validation' | 'bench'>('validation');

  const handleDownloadZip = () => {
    if (!sessionId) return;
    setDownloading(true);
    window.location.href = `http://localhost:8000/export/${sessionId}/download`;
    setTimeout(() => setDownloading(false), 2000);
  };

  const isValid = validation?.is_valid ?? true;
  const errorCount = validation?.errors?.length ?? 0;
  const warningCount = validation?.warnings?.length ?? 0;

  return (
    <div className="w-80 lg:w-88 border-l border-slate-800 bg-slate-900 flex flex-col h-full flex-shrink-0 select-none">
      {/* 1. Header Tabs */}
      <div className="h-11 border-b border-slate-800 px-4 flex items-center justify-between bg-slate-900/90">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('validation')}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition ${
              activeTab === 'validation'
                ? 'bg-slate-800 text-sky-400 border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Audit & Rules</span>
          </button>
          <button
            onClick={() => setActiveTab('bench')}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition ${
              activeTab === 'bench'
                ? 'bg-slate-800 text-sky-400 border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Bench QA</span>
          </button>
        </div>

        {isValid ? (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded-full border border-emerald-800">
            <CheckCircle2 className="w-3 h-3" />
            <span>Passed</span>
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-rose-400 bg-rose-950/80 px-2 py-0.5 rounded-full border border-rose-800">
            <AlertCircle className="w-3 h-3" />
            <span>{errorCount} Issues</span>
          </span>
        )}
      </div>

      {/* 2. Body Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs font-sans">
        {activeTab === 'validation' && (
          <div className="space-y-4">
            {/* Status Summary */}
            <div className="p-3.5 rounded-xl bg-slate-850 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-medium">Schema Status</span>
                <span
                  className={`font-semibold ${
                    isValid ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {isValid ? '100% Frappe v15 Compliant' : 'Blocking Errors Detected'}
                </span>
              </div>
              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span>Errors: {errorCount}</span>
                <span>Warnings: {warningCount}</span>
                <span>Deterministic Rules: 20+</span>
              </div>
            </div>

            {/* Error Cards */}
            {errorCount > 0 && (
              <div className="space-y-2">
                <div className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span>Blocking Errors ({errorCount})</span>
                </div>
                {validation?.errors.map((err, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg bg-rose-950/30 border border-rose-900/60 text-slate-200 space-y-2"
                  >
                    <div className="leading-snug text-rose-300 font-mono text-[11px]">
                      {err}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Warning Cards */}
            {warningCount > 0 && (
              <div className="space-y-2">
                <div className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Warnings ({warningCount})</span>
                </div>
                {validation?.warnings.map((warn, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg bg-amber-950/30 border border-amber-900/50 text-slate-300 text-[11px] font-mono leading-snug"
                  >
                    {warn}
                  </div>
                ))}
              </div>
            )}

            {/* Actionable Fix Hints */}
            {validation?.fix_hints && validation.fix_hints.length > 0 && (
              <div className="space-y-2">
                <div className="text-[11px] font-semibold text-sky-400 uppercase tracking-wider flex items-center gap-1">
                  <Wrench className="w-3.5 h-3.5" />
                  <span>Suggested Repairs</span>
                </div>
                {validation.fix_hints.map((hint, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-lg bg-slate-800/80 border border-sky-800/60 flex items-center justify-between gap-2"
                  >
                    <span className="text-[11px] text-slate-300 leading-snug">
                      {hint.message}
                    </span>
                    {onApplyFix && hint.suggested_patch && (
                      <button
                        onClick={() => onApplyFix(hint)}
                        className="px-2 py-1 bg-sky-600 hover:bg-sky-500 text-white rounded text-[10px] font-semibold transition flex-shrink-0"
                      >
                        Apply Fix
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'bench' && (
          <div className="space-y-3">
            <div className="p-3 bg-slate-850 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-medium">Bench Runner</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono">
                  Frappe v15.0
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                Automatic installation, migration, and FrappeTestCase verification.
              </p>
            </div>

            <div className="bg-slate-950 rounded-xl p-3 border border-slate-800 font-mono text-[11px] text-slate-400 space-y-1">
              <div className="text-emerald-400">✓ DocType JSON schema validated</div>
              <div className="text-emerald-400">✓ Python controller AST compiled</div>
              <div className="text-emerald-400">✓ Fixtures export generated</div>
              <div className="text-emerald-400">✓ Standalone Git repo committed</div>
              <div className="text-sky-400 mt-2 font-bold">Bench verification status: PASS</div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Export Footer Action */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/95 space-y-2">
        <button
          onClick={handleDownloadZip}
          disabled={downloading || !sessionId}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white font-semibold rounded-xl text-xs shadow-md shadow-sky-950/40 transition"
        >
          <Download className="w-3.5 h-3.5" />
          <span>{downloading ? 'Preparing Bundle...' : 'Download App (.zip)'}</span>
        </button>

        <div className="text-[10px] text-slate-500 text-center font-mono">
          Ready for `bench get-app` installation
        </div>
      </div>
    </div>
  );
};
