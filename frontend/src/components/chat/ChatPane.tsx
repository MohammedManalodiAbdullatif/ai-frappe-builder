import React from 'react';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';
import { StageStepper } from './StageStepper';
import { SubagentTeamBar } from './SubagentTeamBar';
import { MessageList } from './MessageList';
import { Composer } from './Composer';
import { EmptyChat } from './EmptyChat';
import { Message, PipelineStage, InterviewQuestion, SubagentActivity } from '../../types';

interface ChatPaneProps {
  stage: PipelineStage;
  substate?: string | null;
  failedStage?: string | null;
  messages: Message[];
  activeQuestion: InterviewQuestion | null;
  coverage?: { basics: number; domain: number } | null;
  hasActiveQuestionOptions?: boolean;
  hasArtifacts: boolean;
  isWorkspaceOpen: boolean;
  onToggleWorkspace: () => void;
  onSendMessage: (text: string) => void;
  onRetryValidation?: () => void;
  isProcessing: boolean;
  isStreaming: boolean;
  subagentActivities?: SubagentActivity[];
}

export const ChatPane: React.FC<ChatPaneProps> = ({
  stage,
  substate,
  failedStage,
  messages,
  activeQuestion,
  coverage,
  hasActiveQuestionOptions = false,
  hasArtifacts,
  isWorkspaceOpen,
  onToggleWorkspace,
  onSendMessage,
  onRetryValidation,
  isProcessing,
  isStreaming,
  subagentActivities = [],
}) => {
  return (
    <div className="flex-1 flex flex-col h-full bg-[var(--bg)] min-w-0 overflow-hidden">
      {/* 48px Minimal Header */}
      <header className="h-12 border-b border-[var(--border)] px-4 flex items-center justify-between flex-shrink-0 z-10 bg-[var(--bg)]">
        <StageStepper
          currentStage={stage}
          substate={substate}
          failedStage={failedStage}
          coverage={coverage}
        />

        {/* Workspace / Flowchart Canvas Toggle */}
        <button
          onClick={onToggleWorkspace}
          className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-card border transition-all ${
            isWorkspaceOpen
              ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
              : 'text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface)] border-[var(--border)]'
          }`}
          title={isWorkspaceOpen ? 'Collapse workspace' : 'Expand workspace & Flowchart canvas'}
          aria-label="Toggle workspace"
        >
          {isWorkspaceOpen ? (
            <PanelRightClose className="w-4 h-4" strokeWidth={1.5} />
          ) : (
            <PanelRightOpen className="w-4 h-4" strokeWidth={1.5} />
          )}
          <span>Workspace</span>
        </button>
      </header>

      {/* Autonomous Subagent Team Live Status Bar */}
      <SubagentTeamBar activities={subagentActivities} />

      {/* Chat Messages Body */}
      {messages.length === 0 ? (
        <EmptyChat onSelectPrompt={onSendMessage} />
      ) : (
        <MessageList
          messages={messages}
          activeQuestion={activeQuestion}
          onSelectOption={onSendMessage}
          onRetryValidation={onRetryValidation}
          isProcessing={isProcessing}
          isStreaming={isStreaming}
        />
      )}

      {/* Composer Pinned to Bottom */}
      <Composer
        onSend={onSendMessage}
        disabled={isProcessing}
        isQuestionActive={hasActiveQuestionOptions}
      />
    </div>
  );
};
