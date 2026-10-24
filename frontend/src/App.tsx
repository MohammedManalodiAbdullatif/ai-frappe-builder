import React, { useState, useEffect } from 'react';
import confetti from 'canvas-confetti';
import { api } from './api';
import {
  Message,
  PipelineStage,
  InterviewQuestion,
  AppMetadata,
  ValidationReport,
} from './types';
import { LeftPanel } from './components/LeftPanel';
import { CentreWorkbench } from './components/CentreWorkbench';
import { RightPanel } from './components/RightPanel';
import { Sparkles, RotateCcw, Radio, CheckCircle, Database } from 'lucide-react';

const STORAGE_KEY_SESSION = 'ai_frappe_session_id';

export const App: React.FC = () => {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY_SESSION) || null;
  });

  const [stage, setStage] = useState<PipelineStage>('discovery');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content:
        "Welcome to AI Frappe App Builder! Describe your business or custom modules. I'll discover requirements one question at a time and generate a clean Frappe v15 app package.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const [activeQuestion, setActiveQuestion] = useState<InterviewQuestion | null>(null);
  const [assumptions, setAssumptions] = useState<string[]>([]);
  const [archetype, setArchetype] = useState<string | undefined>();
  const [app, setApp] = useState<AppMetadata | null>(null);
  const [specRaw, setSpecRaw] = useState<any>(null);
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [sseConnected, setSseConnected] = useState<boolean>(false);

  // Save/clear session storage
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(STORAGE_KEY_SESSION, sessionId);
    } else {
      localStorage.removeItem(STORAGE_KEY_SESSION);
    }
  }, [sessionId]);

  // Connect Server-Sent Events (SSE) when session is active
  useEffect(() => {
    if (!sessionId) {
      setSseConnected(false);
      return;
    }

    const eventSource = api.connectEvents(sessionId, (eventType, data) => {
      setSseConnected(true);
      if (eventType === 'state_change') {
        const nextState = data.to_state as PipelineStage;
        if (nextState) setStage(nextState);
      } else if (eventType === 'question') {
        if (data.question) {
          setActiveQuestion(data.question);
        } else {
          setActiveQuestion(null);
        }
        if (data.assumptions) setAssumptions(data.assumptions);
        if (data.archetype) setArchetype(data.archetype);
      } else if (eventType === 'validation') {
        setValidation(data);
      } else if (eventType === 'spec_patch') {
        // Refetch plan
        api.getPlan(sessionId).then((planData) => {
          if (planData.spec) {
            setSpecRaw(planData.spec);
            if (planData.spec.app) setApp(planData.spec.app);
          }
        });
      }
    });

    eventSource.onopen = () => setSseConnected(true);
    eventSource.onerror = () => setSseConnected(false);

    return () => {
      eventSource.close();
    };
  }, [sessionId]);

  const handleNewSession = () => {
    setSessionId(null);
    setStage('discovery');
    setActiveQuestion(null);
    setAssumptions([]);
    setArchetype(undefined);
    setApp(null);
    setSpecRaw(null);
    setValidation(null);
    setMessages([
      {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content:
          "New session started. Describe your business workflow or custom application requirements.",
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
    setIsProcessing(true);
    setActiveQuestion(null);

    try {
      if (!sessionId) {
        // Start conversation
        const res = await api.startChat(text);
        setSessionId(res.session_id);
        if (res.state) setStage(res.state as PipelineStage);

        const aiMsg: Message = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: res.response || '',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, aiMsg]);

        if (res.question) setActiveQuestion(res.question);
        if (res.assumptions) setAssumptions(res.assumptions);
        if (res.archetype) setArchetype(res.archetype);
        if (res.spec) {
          setSpecRaw(res.spec);
          if (res.spec.app) setApp(res.spec.app);
          else if (res.spec.doctypes) setApp(res.spec);
        }
        if (res.validation) setValidation(res.validation);

        if (res.status === 'ready' || res.state === 'done') {
          confetti({ particleCount: 90, spread: 75, origin: { y: 0.6 } });
        }
      } else {
        // Continue conversation
        const res = await api.sendMessage(sessionId, text);
        if (res.state) setStage(res.state as PipelineStage);

        const aiMsg: Message = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: res.response || '',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, aiMsg]);

        if (res.question) setActiveQuestion(res.question);
        if (res.assumptions) setAssumptions(res.assumptions);
        if (res.archetype) setArchetype(res.archetype);
        if (res.spec) {
          setSpecRaw(res.spec);
          if (res.spec.app) setApp(res.spec.app);
          else if (res.spec.doctypes) setApp(res.spec);
        }
        if (res.validation) setValidation(res.validation);

        if (res.status === 'ready' || res.state === 'done') {
          confetti({ particleCount: 90, spread: 75, origin: { y: 0.6 } });
        }
      }
    } catch (err: any) {
      const errMsg =
        err?.response?.data?.detail || err.message || 'Error communicating with assistant';
      const errorMsg: Message = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `⚠️ Error: ${errMsg}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplyFix = (fixHint: any) => {
    if (!fixHint || !sessionId) return;
    handleSendMessage(`Apply fix: ${fixHint.message}`);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Navbar */}
      <header className="h-12 border-b border-slate-800 bg-slate-900/90 backdrop-blur px-4 flex items-center justify-between flex-shrink-0 z-20 select-none">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-sky-600/20 text-sky-400 border border-sky-500/30">
              <Sparkles className="w-4 h-4" />
            </div>
            <span className="font-bold text-sm tracking-tight text-slate-100">
              AI Frappe App Builder
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              v2.0
            </span>
          </div>

          {app && (
            <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-slate-800">
              <Database className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-xs font-semibold text-slate-300">{app.title}</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          {sessionId && (
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
              <Radio
                className={`w-3.5 h-3.5 ${
                  sseConnected ? 'text-emerald-400 animate-pulse' : 'text-slate-600'
                }`}
              />
              <span>{sseConnected ? 'Live SSE Stream' : 'Connecting...'}</span>
            </div>
          )}

          <button
            onClick={handleNewSession}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>New Session</span>
          </button>
        </div>
      </header>

      {/* Three-Panel Body */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel: Conversation & Stepper */}
        <LeftPanel
          stage={stage}
          messages={messages}
          activeQuestion={activeQuestion}
          assumptions={assumptions}
          archetype={archetype}
          isProcessing={isProcessing}
          onSendMessage={handleSendMessage}
        />

        {/* Centre Panel: Workbench Tabs (ERD, Form, Workflows, Files, JSON) */}
        <CentreWorkbench app={app} specRaw={specRaw} sessionId={sessionId || undefined} />

        {/* Right Panel: Rules Audit & Bench QA */}
        <RightPanel
          sessionId={sessionId || undefined}
          appName={app?.app_name}
          validation={validation}
          onApplyFix={handleApplyFix}
        />
      </main>
    </div>
  );
};
