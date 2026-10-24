import React, { useState } from 'react';
import { FrappeConfig } from '../types';
import { Settings, Check, Globe, Key, ShieldCheck } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  config: FrappeConfig;
  onSave: (config: FrappeConfig) => void;
}

export const SettingsModal: React.FC<Props> = ({ isOpen, onClose, config, onSave }) => {
  const [form, setForm] = useState<FrappeConfig>(config);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(form);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <Settings className="w-5 h-5 text-indigo-600" />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Frappe & Client Configuration</h3>
        </div>
        <p style={{ fontSize: '0.825rem', color: '#64748b', marginBottom: 20 }}>
          Set your Frappe/ERPNext remote server credentials and client name. These are stored locally in your browser.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={14} /> Client / Business Name
            </label>
            <input
              type="text"
              required
              className="form-control"
              placeholder="e.g. Acme Auto Rental"
              value={form.clientName}
              onChange={(e) => setForm({ ...form, clientName: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Globe size={14} /> Remote Frappe Site URL
            </label>
            <input
              type="url"
              required
              className="form-control"
              placeholder="https://mysite.frappe.cloud"
              value={form.frappeUrl}
              onChange={(e) => setForm({ ...form, frappeUrl: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Key size={14} /> Frappe API Key
            </label>
            <input
              type="text"
              required
              className="form-control"
              placeholder="API Key from Frappe User settings"
              value={form.frappeApiKey}
              onChange={(e) => setForm({ ...form, frappeApiKey: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Key size={14} /> Frappe API Secret
            </label>
            <input
              type="password"
              required
              className="form-control"
              placeholder="API Secret from Frappe User settings"
              value={form.frappeApiSecret}
              onChange={(e) => setForm({ ...form, frappeApiSecret: e.target.value })}
            />
          </div>

          <div style={{ margin: '16px 0', borderTop: '1px solid #e2e8f0', paddingTop: 12 }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#4f46e5' }}>LLM Provider (Ollama Cloud / OpenAI)</span>
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Globe size={14} /> LLM Base URL
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="https://ollama.com/v1"
              value={form.llmBaseUrl || 'https://ollama.com/v1'}
              onChange={(e) => setForm({ ...form, llmBaseUrl: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Key size={14} /> LLM API Key
            </label>
            <input
              type="password"
              className="form-control"
              placeholder="Ollama Cloud API Key"
              value={form.llmApiKey || ''}
              onChange={(e) => setForm({ ...form, llmApiKey: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={14} /> Model
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="gemma4:31b"
              value={form.llmModel || 'gemma4:31b'}
              onChange={(e) => setForm({ ...form, llmModel: e.target.value })}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 24 }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              <Check size={16} /> Save Configuration
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
