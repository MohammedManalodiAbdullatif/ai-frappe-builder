import React, { useState } from 'react';
import { Plus, Settings, Menu, X, Box } from 'lucide-react';
import { SessionList } from './SessionList';
import { SettingsDrawer } from './SettingsDrawer';
import { SavedSession, AppSettings } from '../../state/useSession';

interface SidebarProps {
  sessions: SavedSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewApp: () => void;
  settings: AppSettings;
  onUpdateSettings: (newSettings: Partial<AppSettings>) => void;
  sseConnected: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewApp,
  settings,
  onUpdateSettings,
  sseConnected,
}) => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile Toggle Button (< 768px) */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="md:hidden fixed top-3 left-3 z-40 p-2 rounded-card bg-[var(--surface)] border border-[var(--border)] text-[var(--text)]"
        aria-label="Toggle navigation"
      >
        {mobileOpen ? <X className="w-4 h-4" strokeWidth={1.5} /> : <Menu className="w-4 h-4" strokeWidth={1.5} />}
      </button>

      {/* Backdrop for mobile */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="md:hidden fixed inset-0 z-30 bg-black/60 backdrop-blur-sm"
        />
      )}

      {/* Main Sidebar Column (260px) */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-30 w-[260px] flex-shrink-0 flex flex-col bg-[var(--bg-side)] border-r border-[var(--border)] transition-transform duration-200 ease-in-out ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Brand / New App Button */}
        <div className="p-3 border-b border-[var(--border)]">
          <button
            onClick={() => {
              onNewApp();
              setMobileOpen(false);
            }}
            className="flex items-center justify-between w-full px-3 py-2 bg-[var(--surface)] hover:border-[var(--accent)] border border-[var(--border)] rounded-card text-sm font-medium text-[var(--text)] transition-colors"
          >
            <div className="flex items-center gap-2">
              <Box className="w-4 h-4 text-[var(--accent)]" strokeWidth={1.5} />
              <span>New app</span>
            </div>
            <Plus className="w-4 h-4 text-[var(--muted)]" strokeWidth={1.5} />
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto py-2">
          <SessionList
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={(id) => {
              onSelectSession(id);
              setMobileOpen(false);
            }}
          />
        </div>

        {/* Bottom Pinned Settings */}
        <div className="p-3 border-t border-[var(--border)] bg-[var(--bg-side)]">
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-2 w-full px-2.5 py-2 rounded-card text-sm text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface)] transition-colors"
          >
            <Settings className="w-4 h-4" strokeWidth={1.5} />
            <span>Settings</span>
          </button>
        </div>
      </aside>

      {/* Settings Modal Drawer */}
      <SettingsDrawer
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={settings}
        onUpdateSettings={onUpdateSettings}
        sseConnected={sseConnected}
      />
    </>
  );
};
