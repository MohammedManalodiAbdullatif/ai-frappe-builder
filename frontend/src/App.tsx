import React, { useState, useEffect } from 'react';
import confetti from 'canvas-confetti';
import { api } from './api';
import { Message, Question, BuildResponse, BuildStatus } from './types';
import { ChatPane } from './components/ChatPane';
import { RightPane } from './components/RightPane';
import { Sparkles, RotateCcw } from 'lucide-react';

const STORAGE_KEY_SESSION = 'ai_frappe_session_id';

export const App: React.FC = () => {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY_SESSION) || null;
  });

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content:
        "Hello! I am your AI Frappe App Builder. Tell me what kind of business or module you want to build. I will ask you questions one by one and build a complete installable Frappe app that you can download as a .zip or push to Git.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const [questions, setQuestions] = useState<Question[]>([]);
  const [buildData, setBuildData] = useState<BuildResponse | null>(null);
  const [status, setStatus] = useState<BuildStatus>('idle');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Save session ID changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(STORAGE_KEY_SESSION, sessionId);
    } else {
      localStorage.removeItem(STORAGE_KEY_SESSION);
    }
  }, [sessionId]);

  const handleNewSession = () => {
    setSessionId(null);
    setBuildData(null);
    setQuestions([]);
    setStatus('idle');
    setMessages([
      {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content:
          "New session started. Describe what business processes or custom modules you want to build in Frappe.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  const handleSendMessage = async (text: string) => {
    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      if (!sessionId) {
        // Start new session
        const res = await api.startChat(text);
        setSessionId(res.session_id);
        setStatus(res.status as BuildStatus);

        const aiMsg: Message = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: res.response || (res.status === 'ready' ? 'App Spec generated and packaged successfully!' : ''),
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, aiMsg]);
        setQuestions(res.questions || []);

        const buildResp: BuildResponse = {
          session_id: res.session_id,
          status: res.status as BuildStatus,
          created: res.created || [],
          errors: res.errors || [],
          preview_urls: res.preview_urls || [],
          questions: res.questions || [],
          assumptions: res.assumptions || [],
          spec: res.spec || null,
        };
        setBuildData(buildResp);

        if (res.status === 'done') {
          confetti({ particleCount: 80, spread: 70, origin: { y: 0.6 } });
        }
      } else {
        // Continue existing session
        const res = await api.sendMessage(sessionId, text);
        setStatus(res.status as BuildStatus);

        const aiMsg: Message = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: res.response || (res.status === 'ready' ? 'App Spec updated and packaged!' : ''),
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, aiMsg]);
        setQuestions(res.questions || []);

        const buildResp: BuildResponse = {
          session_id: sessionId,
          status: res.status as BuildStatus,
          created: res.created || [],
          errors: res.errors || [],
          preview_urls: res.preview_urls || [],
          questions: res.questions || [],
          assumptions: res.assumptions || [],
          spec: res.spec || null,
        };
        setBuildData(buildResp);

        if (res.status === 'done') {
          confetti({ particleCount: 90, spread: 80, origin: { y: 0.6 } });
        }
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err.message || 'Error communicating with AI Frappe service';
      const errorBubble: Message = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `⚠️ Error: ${errMsg}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorBubble]);
      setStatus('failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <header className="app-header">
        <div className="brand">
          <Sparkles className="w-5 h-5" />
          <span>AI Frappe App Builder</span>
          <span className="brand-badge">Export Engine</span>
          <span className={`status-chip ${status}`}>{status}</span>
        </div>

        <div className="header-actions">
          <button className="btn btn-outline" onClick={handleNewSession}>
            <RotateCcw size={15} /> New Session
          </button>
        </div>
      </header>

      <main className="app-container">
        <ChatPane
          messages={messages}
          questions={questions}
          isLoading={isLoading}
          onSendMessage={handleSendMessage}
          status={status}
        />
        <RightPane
          buildData={buildData}
          sessionId={sessionId}
        />
      </main>
    </>
  );
};
