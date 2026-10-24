import React, { useState, useEffect } from 'react';
import confetti from 'canvas-confetti';
import { useSession } from './state/useSession';
import { Sidebar } from './components/sidebar/Sidebar';
import { ChatPane } from './components/chat/ChatPane';
import { Workspace } from './components/workspace/Workspace';

export const App: React.FC = () => {
  const {
    sessionId,
    sessions,
    settings,
    messages,
    stage,
    activeQuestion,
    app,
    specRaw,
    validation,
    isProcessing,
    isStreaming,
    sseConnected,
    startNewSession,
    selectSession,
    sendMessage,
    updateSettings,
  } = useSession();

  const [isWorkspaceOpen, setIsWorkspaceOpen] = useState(false);
  const hasArtifacts = !!(app && app.doctypes && app.doctypes.length > 0);

  // Auto-open workspace when data model / app is first generated
  useEffect(() => {
    if (hasArtifacts && stage !== 'discovery') {
      setIsWorkspaceOpen(true);
    }
  }, [hasArtifacts, stage]);

  // Celebrate with confetti when ready
  useEffect(() => {
    if (stage === 'done') {
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.8 },
      });
    }
  }, [stage]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg)] text-[var(--text)]">
      {/* 1. Left Sidebar (260px) */}
      <Sidebar
        sessions={sessions}
        activeSessionId={sessionId}
        onSelectSession={selectSession}
        onNewApp={startNewSession}
        settings={settings}
        onUpdateSettings={updateSettings}
        sseConnected={sseConnected}
      />

      {/* 2. Main Chat (centered, max-width 760px) */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <ChatPane
          stage={stage}
          messages={messages}
          activeQuestion={activeQuestion}
          hasArtifacts={hasArtifacts}
          isWorkspaceOpen={isWorkspaceOpen}
          onToggleWorkspace={() => setIsWorkspaceOpen(!isWorkspaceOpen)}
          onSendMessage={sendMessage}
          isProcessing={isProcessing}
          isStreaming={isStreaming}
        />
      </main>

      {/* 3. Slide-in Workspace (0px closed / 480px open) */}
      <Workspace
        isOpen={isWorkspaceOpen}
        onClose={() => setIsWorkspaceOpen(false)}
        app={app}
        specRaw={specRaw}
        sessionId={sessionId}
        stage={stage}
        validation={validation}
      />
    </div>
  );
};
