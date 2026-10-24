import React from 'react';
import { Layers, FileText, GitBranch, FolderGit2, Braces } from 'lucide-react';

export type WorkspaceTabId = 'erd' | 'forms' | 'workflows' | 'files' | 'spec';

interface WorkspaceTabsProps {
  activeTab: WorkspaceTabId;
  onSelectTab: (tab: WorkspaceTabId) => void;
}

const TABS: { id: WorkspaceTabId; label: string; icon: React.FC<any> }[] = [
  { id: 'erd', label: 'Data model', icon: Layers },
  { id: 'forms', label: 'Forms', icon: FileText },
  { id: 'workflows', label: 'Workflows', icon: GitBranch },
  { id: 'files', label: 'Files', icon: FolderGit2 },
  { id: 'spec', label: 'Spec', icon: Braces },
];

export const WorkspaceTabs: React.FC<WorkspaceTabsProps> = ({
  activeTab,
  onSelectTab,
}) => {
  return (
    <div className="flex items-center h-11 border-b border-[var(--border)] px-3 gap-1 bg-[var(--surface)] overflow-x-auto select-none no-scrollbar">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onSelectTab(tab.id)}
            className={`relative flex items-center gap-1.5 px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors ${
              isActive
                ? 'text-[var(--text)] font-semibold'
                : 'text-[var(--muted)] hover:text-[var(--text)]'
            }`}
          >
            <Icon className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.5} />
            <span>{tab.label}</span>
            {isActive && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-[var(--accent)]" />
            )}
          </button>
        );
      })}
    </div>
  );
};
