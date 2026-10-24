import React from 'react';
import { MessageSquare, Sparkles } from 'lucide-react';
import { SavedSession } from '../../state/useSession';

interface SessionListProps {
  sessions: SavedSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
}

export const SessionList: React.FC<SessionListProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
}) => {
  if (sessions.length === 0) {
    return (
      <div className="px-3 py-6 text-center text-muted">
        No recent apps
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 overflow-y-auto px-2 py-1">
      <div className="px-2 py-1 text-xs font-medium text-muted">
        Recent
      </div>
      {sessions.map((sess) => {
        const isActive = sess.id === activeSessionId;
        return (
          <button
            key={sess.id}
            onClick={() => onSelectSession(sess.id)}
            className={`flex items-center gap-2 w-full px-2.5 py-2 text-left rounded-card transition-colors text-sm truncate ${
              isActive
                ? 'bg-[var(--surface)] text-[var(--text)] font-medium border border-[var(--border)]'
                : 'text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface)]/50'
            }`}
          >
            <MessageSquare className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
            <span className="truncate">{sess.title}</span>
          </button>
        );
      })}
    </div>
  );
};
