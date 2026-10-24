import axios from 'axios';
import { BuildResponse, FileNode, FrappeConfig } from './types';

const API_BASE = 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 180000, // 3 minutes timeout for LLM synthesis and healing
});

export const api = {
  async health(): Promise<{ status: string }> {
    const res = await client.get('/health');
    return res.data;
  },

  async startChat(message: string, clientName: string = 'Frappe Client'): Promise<any> {
    const res = await client.post('/api/v1/chat/start', {
      client_name: clientName,
      message,
    });
    return res.data;
  },

  async sendMessage(sessionId: string, message: string): Promise<any> {
    const res = await client.post('/api/v1/chat/message', {
      session_id: sessionId,
      message,
    });
    return res.data;
  },

  async oneShotBuild(config: FrappeConfig, description: string): Promise<BuildResponse> {
    const res = await client.post('/build', {
      client_name: config.clientName,
      description,
      frappe_url: config.frappeUrl,
      frappe_api_key: config.frappeApiKey,
      frappe_api_secret: config.frappeApiSecret,
    });
    return res.data;
  },

  async getPlan(sessionId: string): Promise<any> {
    const res = await client.get(`/api/v1/plan/${sessionId}`);
    return res.data;
  },

  async exportApp(sessionId: string, gitRemote?: string): Promise<any> {
    const res = await client.post(`/api/v1/export/${sessionId}`, {
      output_dir: '/tmp/frappe_exports',
      git_remote: gitRemote || null,
    });
    return res.data;
  },

  async getExportTree(sessionId: string): Promise<FileNode> {
    const res = await client.get(`/api/v1/export/${sessionId}/tree`);
    return res.data;
  },

  async getExportFile(sessionId: string, filePath: string): Promise<{ path: string; content: string }> {
    const res = await client.get(`/api/v1/export/${sessionId}/file`, {
      params: { path: filePath },
    });
    return res.data;
  },

  async getSessions(): Promise<any[]> {
    const res = await axios.get(`${API_BASE}/sessions`);
    return res.data;
  },

  async getSessionDetail(sessionId: string): Promise<any> {
    const res = await axios.get(`${API_BASE}/sessions/${sessionId}`);
    return res.data;
  },

  connectEvents(sessionId: string, onEvent: (eventType: string, data: any) => void): EventSource {
    const es = new EventSource(`${API_BASE}/api/v1/sessions/${sessionId}/events`);
    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        onEvent('message', payload);
      } catch (err) {
        console.error('Failed to parse SSE event data', err);
      }
    };
    es.addEventListener('token', (e: any) => {
      try {
        onEvent('token', JSON.parse(e.data));
      } catch {}
    });
    es.addEventListener('question', (e: any) => {
      try {
        onEvent('question', JSON.parse(e.data));
      } catch {}
    });
    es.addEventListener('state_change', (e: any) => {
      try {
        onEvent('state_change', JSON.parse(e.data));
      } catch {}
    });
    es.addEventListener('validation', (e: any) => {
      try {
        onEvent('validation', JSON.parse(e.data));
      } catch {}
    });
    es.addEventListener('spec_patch', (e: any) => {
      try {
        onEvent('spec_patch', JSON.parse(e.data));
      } catch {}
    });
    return es;
  },
};
