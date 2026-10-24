import React from 'react';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';
import { StageStepper } from './StageStepper';
import { MessageList } from './MessageList';
import { Composer } from './Composer';
import { EmptyChat } from './EmptyChat';
import { Message, PipelineStage, InterviewQuestion } from '../../types';

interface ChatPaneProps {
  stage: PipelineStage;
  messages: Message[];
  activeQuestion: InterviewQuestion | null;
  hasArtifacts: boolean;
  isWorkspaceOpen: boolean;
  onToggleWorkspace: () => void;
  onSendMessage: (text: string) => void;
  isProcessing: boolean;
  isStreaming: boolean;
}

export const ChatPane: React.FC<ChatPaneProps> = ({
  stage,
  messages,
  activeQuestion,
  hasArtifacts,
  isWorkspaceOpen,
  onToggleWorkspace,
  onSendMessage,
  isProcessing,
  isStreaming,
}) => {
  return (
    <div className="flex-1 flex flex-col h-full bg-[var(--bg)] min-w-0 overflow-hidden">
      {/* 48px Minimal Header */}
      <header className="h-12 border-b border-[var(--border)] px-4 flex items-center justify-between flex-shrink-0 z-10 bg-[var(--bg)]">
        <StageStepper currentStage={stage} />

        {/* Workspace toggle icon (only shown when artifacts exist) */}
        {hasArtifacts && (
          <button
            onClick={onToggleWorkspace}
            className="flex items-center gap-1.5 p-1.5 text-xs font-medium text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface)] rounded-card transition-colors"
            title={isWorkspaceOpen ? 'Collapse workspace' : 'Expand workspace'}
            aria-label="Toggle workspace"
          >
            {isWorkspaceOpen ? (
              <PanelRightClose className="w-4 h-4" strokeWidth={1.5} />
            ) : (
              <PanelRightOpen className="w-4 h-4" strokeWidth={1.5} />
            )}
            <span className="hidden sm:inline">Workspace</span>
          </button>
        )}
      </header>

      {/* Chat Messages Body */}
      {messages.length === 0 ? (
        <EmptyChat onSelectPrompt={onSendMessage} />
      ) : (
        <MessageList
          messages={messages}
          activeQuestion={activeQuestion}
          onSelectOption={onSendMessage}
          isProcessing={isProcessing}
          isStreaming={isStreaming}
        />
      )}

      {/* Composer Pinned to Bottom */}
      <Composer onSend={onSendMessage} disabled={isProcessing} />
    </div>
  );
};
