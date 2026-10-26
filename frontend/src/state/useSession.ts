import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api';
import {
  Message,
  PipelineStage,
  InterviewQuestion,
  InterviewTurn,
  AppMetadata,
  ValidationReport,
  SubagentActivity,
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
  frappeUrl?: string;
  frappeApiKey?: string;
  frappeApiSecret?: string;
}

const STORAGE_KEY_SESSIONS = 'ai_frappe_sessions_v2';
const STORAGE_KEY_ACTIVE = 'ai_frappe_active_session_v2';
const STORAGE_KEY_SETTINGS = 'ai_frappe_settings_v2';

const DEFAULT_SETTINGS: AppSettings = {
  model: 'gemma4:31b',
  frappeVersion: 'v15',
  erpnextRequired: true,
  theme: 'dark',
  frappeUrl: 'http://crm.localhost:8015',
  frappeApiKey: '992f21dbfdb7f47',
  frappeApiSecret: 'acf9538d97bf2a6',
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
  const [substate, setSubstate] = useState<string | null>(null);
  const [failedStage, setFailedStage] = useState<string | null>(null);
  const [qaReport, setQaReport] = useState<any>(null);
  const [activeQuestion, setActiveQuestion] = useState<InterviewQuestion | null>(null);
  const [activeTurn, setActiveTurn] = useState<InterviewTurn | null>(null);
  const [coverage, setCoverage] = useState<{ basics: number; domain: number }>({ basics: 0, domain: 0 });
  const [assumptions, setAssumptions] = useState<string[]>([]);
  const [app, setApp] = useState<AppMetadata | null>(null);
  const [specRaw, setSpecRaw] = useState<any>(null);
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [subagentActivities, setSubagentActivities] = useState<SubagentActivity[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<any>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [sseConnected, setSseConnected] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);

  // Safety watchdog: ensure isProcessing never gets permanently stuck
  useEffect(() => {
    if (!isProcessing) return;
    const timer = setTimeout(() => {
      console.warn('isProcessing timeout watchdog: auto-clearing stuck processing state');
      setIsProcessing(false);
      setIsStreaming(false);
    }, 20000);
    return () => clearTimeout(timer);
  }, [isProcessing]);

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
        if (data.substate !== undefined) setSubstate(data.substate);
        if (data.failed_stage !== undefined) setFailedStage(data.failed_stage);
      } else if (eventType === 'qa_report') {
        setQaReport(data);
      } else if (eventType === 'interview_turn') {
        const turn = data as InterviewTurn;
        if (turn.assumptions) setAssumptions(turn.assumptions);
        if (turn.coverage) setCoverage(turn.coverage);
        setActiveTurn(turn);
        if (turn.question) {
          setActiveQuestion({
            id: turn.question.id,
            question: turn.question.text,
            reason: turn.question.help || undefined,
            options: (turn.question.options || []).map((o) => ({
              label: o.label,
              value: o.value,
              description: o.description || undefined,
            })),
          });
        } else {
          setActiveQuestion(null);
        }

        // Attach interview_turn to latest assistant message or append a new one
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant') {
            return [
              ...prev.slice(0, -1),
              {
                ...last,
                content: turn.say || last.content,
                interview_turn: turn,
              },
            ];
          }
          return [
            ...prev,
            {
              id: Date.now().toString(),
              role: 'assistant',
              content: turn.say,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              interview_turn: turn,
            },
          ];
        });
      } else if (eventType === 'message') {
        const content = data.content || data.say || '';
        if (content) {
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  content: content || last.content,
                },
              ];
            }
            return [
              ...prev,
              {
                id: Date.now().toString(),
                role: 'assistant',
                content,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              },
            ];
          });
        }
      } else if (eventType === 'question') {
        if (data.question) {
          setActiveQuestion(data.question);
        } else {
          setActiveQuestion(null);
        }
        if (data.assumptions) setAssumptions(data.assumptions);
      } else if (eventType === 'validation') {
        setValidation(data);
      } else if (eventType === 'subagent_activity') {
        const activity = data as SubagentActivity;
        setSubagentActivities((prev) => {
          const filtered = prev.filter((a) => a.agent !== activity.agent);
          return [
            ...filtered,
            {
              ...activity,
              timestamp:
                activity.timestamp ||
                new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ];
        });
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
      // 1. Restore chat messages
      try {
        const detail = await api.getSessionDetail(id);
        if (detail && Array.isArray(detail.messages) && detail.messages.length > 0) {
          const restoredMessages: Message[] = detail.messages.map((m: any, idx: number) => ({
            id: m.id || `${id}-${idx}`,
            role: m.role,
            content: m.content,
            interview_turn: m.interview_turn || undefined,
            timestamp: m.created_at
              ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }));
          setMessages(restoredMessages);
        }

        if (detail?.interview_turn) {
          setActiveTurn(detail.interview_turn);
          if (detail.interview_turn.question) {
            setActiveQuestion({
              id: detail.interview_turn.question.id,
              question: detail.interview_turn.question.text,
              reason: detail.interview_turn.question.help || undefined,
              options: (detail.interview_turn.question.options || []).map((o: any) => ({
                label: o.label,
                value: o.value,
                description: o.description || undefined,
              })),
            });
          }
        }
        if (detail?.coverage) setCoverage(detail.coverage);
        if (detail?.assumptions) setAssumptions(detail.assumptions);
      } catch (detailErr) {
        console.warn('Could not load session messages:', detailErr);
      }

      // 2. Restore plan data
      const planData = await api.getPlan(id);
      if (planData && (planData.app || planData.spec)) {
        const appData = planData.app || (planData.spec?.app ? planData.spec.app : planData.spec);
        setApp(appData);
        setSpecRaw(planData);
        setStage(
          planData.status === 'ready' || planData.spec?.status === 'ready'
            ? 'done'
            : 'drafting'
        );
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

  // Restore active session on initial mount
  useEffect(() => {
    const initialSessionId = localStorage.getItem(STORAGE_KEY_ACTIVE);
    if (initialSessionId) {
      loadSession(initialSessionId);
    }
  }, [loadSession]);

  const selectSession = useCallback((id: string) => {
    setSessionId(id);
    setMessages([]);
    setActiveQuestion(null);
    setAssumptions([]);
    setApp(null);
    setSpecRaw(null);
    setValidation(null);
    setSubagentActivities([]);
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
    setSubagentActivities([]);

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

    // Collapse previous question card if active and append user message
    setMessages((prev) => {
      const updated = prev.map((m, idx) => {
        if (
          idx === prev.length - 1 &&
          m.role === 'assistant' &&
          m.interview_turn?.question &&
          !m.answeredAnswer
        ) {
          return { ...m, answeredAnswer: text };
        }
        return m;
      });
      return [...updated, userMsg];
    });

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

      const turn = resp.interview_turn as InterviewTurn | undefined;
      if (turn) {
        if (turn.coverage) setCoverage(turn.coverage);
        if (turn.assumptions) setAssumptions(turn.assumptions);
        setActiveTurn(turn);
      } else if (resp.coverage) {
        setCoverage(resp.coverage);
      }

      // Append assistant message only if not already delivered via SSE, or enrich existing
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant') {
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              content: turn?.say || resp.response || last.content,
              interview_turn: turn || last.interview_turn,
            },
          ];
        }
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: turn?.say || resp.response || 'App spec updated.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          interview_turn: turn,
        };
        return [...prev, assistantMsg];
      });

      if (resp.status) {
        setStage(resp.status === 'ready' ? 'done' : 'discovery');
      }

      if (resp.questions && resp.questions.length > 0) {
        const q = resp.questions[0];
        setActiveQuestion({
          id: q.id || 'q1',
          question: q.text || q.question,
          reason: q.help || q.why_it_matters || q.reason,
          options: q.options || [],
        });
      } else {
        setActiveQuestion(null);
      }

      if (resp.assumptions) {
        setAssumptions(resp.assumptions);
      }

      if (resp.spec) {
        const appData = resp.spec.app ? resp.spec.app : resp.spec;
        setApp(appData);
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

  const retryValidation = useCallback(async () => {
    if (isProcessing) return;
    await sendPrompt("Retry validation", sessionId);
  }, [isProcessing, sessionId]);

  const updateSettings = useCallback((newSettings: Partial<AppSettings>) => {
    setSettings((prev) => ({ ...prev, ...newSettings }));
  }, []);

  const updateAppPlan = useCallback(
    async (updatedApp: AppMetadata) => {
      setApp(updatedApp);
      if (!sessionId) return;
      try {
        const planData = await api.updatePlan(sessionId, updatedApp);
        if (planData.app) {
          setApp(planData.app);
          setSpecRaw(planData);
        }
        if (planData.validation) {
          setValidation(planData.validation);
        }
      } catch (err) {
        console.error('Failed to update app plan:', err);
      }
    },
    [sessionId]
  );

  const applyToFrappe = useCallback(async () => {
    if (!sessionId || isApplying) return;
    setIsApplying(true);
    setApplyResult(null);
    try {
      const res = await api.applySession(sessionId, {
        frappe_url: settings.frappeUrl,
        frappe_api_key: settings.frappeApiKey,
        frappe_api_secret: settings.frappeApiSecret,
      });
      setApplyResult(res);
      return res;
    } catch (err: any) {
      console.error('Failed to apply to Frappe:', err);
      setApplyResult({
        status: 'failed',
        errors: [err.response?.data?.detail || err.message],
      });
    } finally {
      setIsApplying(false);
    }
  }, [sessionId, isApplying, settings]);

  const hasActiveQuestionOptions = Boolean(
    (activeTurn?.question?.options && activeTurn.question.options.length > 0) ||
      (activeQuestion?.options && activeQuestion.options.length > 0)
  );

  return {
    sessionId,
    sessions,
    settings,
    messages,
    stage,
    substate,
    failedStage,
    qaReport,
    activeQuestion,
    activeTurn,
    coverage,
    hasActiveQuestionOptions,
    assumptions,
    app,
    specRaw,
    validation,
    subagentActivities,
    isProcessing,
    isStreaming,
    streamingContent,
    sseConnected,
    isApplying,
    applyResult,
    applyToFrappe,
    startNewSession,
    selectSession,
    sendMessage,
    retryValidation,
    updateSettings,
    updateAppPlan,
  };
}
