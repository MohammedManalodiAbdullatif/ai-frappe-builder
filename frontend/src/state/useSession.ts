import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api';
import {
  Message,
  PipelineStage,
  InterviewQuestion,
  AppMetadata,
  ValidationReport,
} from '../types';

export interface SavedSession {
  id: string;
  title: string;
  createdAt: string;
}

export interface AppSettings {
  model: string;
  frappeVersion: string;
  erpnextRequired: boolean;
  theme: string;
}

const STORAGE_KEY_SESSIONS = 'ai_frappe_sessions_v2';
const STORAGE_KEY_ACTIVE = 'ai_frappe_active_session_v2';
const STORAGE_KEY_SETTINGS = 'ai_frappe_settings_v2';

const DEFAULT_SETTINGS: AppSettings = {
  model: 'gemma4:31b',
  frappeVersion: 'v15',
  erpnextRequired: true,
  theme: 'dark',
};

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY_ACTIVE) || null;
  });

  const [sessions, setSessions] = useState<SavedSession[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_SESSIONS);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_SETTINGS);
      return stored ? { ...DEFAULT_SETTINGS, ...JSON.parse(stored) } : DEFAULT_SETTINGS;
    } catch {
      return DEFAULT_SETTINGS;
    }
  });

  const [messages, setMessages] = useState<Message[]>([]);
  const [stage, setStage] = useState<PipelineStage>('discovery');
  const [activeQuestion, setActiveQuestion] = useState<InterviewQuestion | null>(null);
  const [assumptions, setAssumptions] = useState<string[]>([]);
  const [app, setApp] = useState<AppMetadata | null>(null);
  const [specRaw, setSpecRaw] = useState<any>(null);
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [sseConnected, setSseConnected] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);

  // Sync sessions list to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(sessions));
    } catch (e) {
      console.error('Failed to store sessions', e);
    }
  }, [sessions]);

  // Sync settings to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_SETTINGS, JSON.stringify(settings));
    } catch (e) {
      console.error('Failed to store settings', e);
    }
  }, [settings]);

  // Sync active sessionId to localStorage
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(STORAGE_KEY_ACTIVE, sessionId);
    } else {
      localStorage.removeItem(STORAGE_KEY_ACTIVE);
    }
  }, [sessionId]);

  // SSE Event Listener
  useEffect(() => {
    if (!sessionId) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setSseConnected(false);
      return;
    }

    const es = api.connectEvents(sessionId, (eventType, data) => {
      setSseConnected(true);
      if (eventType === 'state_change' || eventType === 'stage_transition') {
        const nextState = (data.to_state || data.state) as PipelineStage;
        if (nextState) setStage(nextState.toLowerCase() as PipelineStage);
      } else if (eventType === 'question') {
        if (data.question) {
          setActiveQuestion(data.question);
        } else {
          setActiveQuestion(null);
        }
        if (data.assumptions) setAssumptions(data.assumptions);
      } else if (eventType === 'validation') {
        setValidation(data);
      } else if (eventType === 'spec_patch' || eventType === 'agent_run') {
        if (data.output?.app) {
          setApp(data.output.app);
          setSpecRaw(data.output);
        } else {
          api.getPlan(sessionId).then((planData) => {
            if (planData.app) {
              setApp(planData.app);
              setSpecRaw(planData);
            }
          });
        }
      } else if (eventType === 'token') {
        if (data.token) {
          setIsStreaming(true);
          setStreamingContent((prev) => prev + data.token);
        }
      }
    });

    eventSourceRef.current = es;

    return () => {
      es.close();
      eventSourceRef.current = null;
      setSseConnected(false);
    };
  }, [sessionId]);

  // Load existing session details if available
  const loadSession = useCallback(async (id: string) => {
    try {
      setIsProcessing(true);
      const planData = await api.getPlan(id);
      if (planData && planData.app) {
        setApp(planData.app);
        setSpecRaw(planData);
        setStage(planData.status === 'ready' ? 'done' : 'drafting');
        if (planData.validation) {
          setValidation(planData.validation);
        }
      }
    } catch {
      // New or uninitialized session
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const selectSession = useCallback((id: string) => {
    setSessionId(id);
    setMessages([]);
    setActiveQuestion(null);
    setAssumptions([]);
    setApp(null);
    setSpecRaw(null);
    setValidation(null);
    setStage('discovery');
    loadSession(id);
  }, [loadSession]);

  const startNewSession = useCallback(async (initialPrompt?: string) => {
    setSessionId(null);
    setMessages([]);
    setStage('discovery');
    setActiveQuestion(null);
    setAssumptions([]);
    setApp(null);
    setSpecRaw(null);
    setValidation(null);

    if (initialPrompt) {
      await sendPrompt(initialPrompt, null);
    }
  }, []);

  const sendPrompt = async (text: string, currentSessionId: string | null) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);
    setIsStreaming(true);
    setStreamingContent('');

    try {
      let resp: any;
      if (!currentSessionId) {
        resp = await api.startChat(text, 'Frappe Client');
        const newId = resp.session_id;
        setSessionId(newId);

        // Add to recent sessions
        const title = text.slice(0, 32).trim() + (text.length > 32 ? '…' : '');
        setSessions((prev) => [
          { id: newId, title: title || 'New Frappe App', createdAt: new Date().toISOString() },
          ...prev.filter((s) => s.id !== newId),
        ]);
      } else {
        resp = await api.sendMessage(currentSessionId, text);
      }

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: resp.response || 'App spec updated.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      if (resp.status) {
        setStage(resp.status === 'ready' ? 'done' : 'discovery');
      }

      if (resp.questions && resp.questions.length > 0) {
        const q = resp.questions[0];
        setActiveQuestion({
          id: q.id || 'q1',
          question: q.question,
          reason: q.why_it_matters || q.reason,
          options: q.options || [],
        });
      } else {
        setActiveQuestion(null);
      }

      if (resp.assumptions) {
        setAssumptions(resp.assumptions);
      }

      if (resp.spec) {
        setApp(resp.spec);
        setSpecRaw(resp);
      }

      if (resp.validation) {
        setValidation(resp.validation);
      }
    } catch (err: any) {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${err.response?.data?.detail || err.message}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsProcessing(false);
      setIsStreaming(false);
      setStreamingContent('');
    }
  };

  const sendMessage = useCallback(async (text: string) => {
    if (isProcessing) return;
    await sendPrompt(text, sessionId);
  }, [isProcessing, sessionId]);

  const updateSettings = useCallback((newSettings: Partial<AppSettings>) => {
    setSettings((prev) => ({ ...prev, ...newSettings }));
  }, []);

  return {
    sessionId,
    sessions,
    settings,
    messages,
    stage,
    activeQuestion,
    assumptions,
    app,
    specRaw,
    validation,
    isProcessing,
    isStreaming,
    streamingContent,
    sseConnected,
    startNewSession,
    selectSession,
    sendMessage,
    updateSettings,
  };
}
