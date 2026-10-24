import React, { useState } from 'react';
import { WorkspaceTabs, WorkspaceTabId } from './WorkspaceTabs';
import { StatusBar } from './StatusBar';
import { ErdPanel } from './panels/ErdPanel';
import { FormsPanel } from './panels/FormsPanel';
import { WorkflowsPanel } from './panels/WorkflowsPanel';
import { FilesPanel } from './panels/FilesPanel';
import { SpecPanel } from './panels/SpecPanel';
import { AppMetadata, ValidationReport, PipelineStage } from '../../types';
import { X } from 'lucide-react';

interface WorkspaceProps {
  isOpen: boolean;
  onClose: () => void;
  app: AppMetadata | null;
  specRaw: any;
  sessionId: string | null;
  stage: PipelineStage;
  validation: ValidationReport | null;
}

export const Workspace: React.FC<WorkspaceProps> = ({
  isOpen,
  onClose,
  app,
  specRaw,
  sessionId,
  stage,
  validation,
}) => {
  const [activeTab, setActiveTab] = useState<WorkspaceTabId>('erd');

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop for screens < 1024px */}
      <div
        onClick={onClose}
        className="lg:hidden fixed inset-0 z-20 bg-black/50 backdrop-blur-sm"
      />

      {/* Workspace Panel */}
      <aside
        className={`fixed lg:static inset-y-0 right-0 z-30 w-full lg:w-[480px] flex-shrink-0 flex flex-col bg-[var(--surface)] border-l border-[var(--border)] transition-workspace overflow-hidden shadow-none`}
      >
        {/* Top Header / Tabs */}
        <div className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--surface)]">
          <div className="flex-1 overflow-x-auto">
            <WorkspaceTabs activeTab={activeTab} onSelectTab={setActiveTab} />
          </div>
          <button
            onClick={onClose}
            className="p-2 mr-2 rounded-card text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--border)] lg:hidden"
            aria-label="Close workspace"
          >
            <X className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        {/* Tab Body */}
        <div className="flex-1 flex flex-col min-h-0 bg-[var(--bg)] overflow-hidden">
          {activeTab === 'erd' && <ErdPanel app={app} />}
          {activeTab === 'forms' && <FormsPanel app={app} />}
          {activeTab === 'workflows' && <WorkflowsPanel app={app} />}
          {activeTab === 'files' && <FilesPanel sessionId={sessionId} />}
          {activeTab === 'spec' && <SpecPanel app={app} specRaw={specRaw} />}
        </div>

        {/* Bottom Status Bar */}
        <StatusBar sessionId={sessionId} stage={stage} validation={validation} />
      </aside>
    </>
  );
};
