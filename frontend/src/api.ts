import axios from 'axios';
import { BuildResponse, FrappeConfig } from './types';

const API_BASE = 'http://localhost:8000';

export const api = {
  async health(): Promise<{ status: string }> {
    const res = await axios.get(`${API_BASE}/health`);
    return res.data;
  },

  async startChat(message: string, clientName: string = 'Frappe Client'): Promise<any> {
    const res = await axios.post(`${API_BASE}/chat/start`, {
      client_name: clientName,
      message,
    });
    return res.data;
  },

  async sendMessage(sessionId: string, message: string): Promise<any> {
    const res = await axios.post(`${API_BASE}/chat/message`, {
      session_id: sessionId,
      message,
    });
    return res.data;
  },

  async oneShotBuild(config: FrappeConfig, description: string): Promise<BuildResponse> {
    const res = await axios.post(`${API_BASE}/build`, {
      client_name: config.clientName,
      description,
      frappe_url: config.frappeUrl,
      frappe_api_key: config.frappeApiKey,
      frappe_api_secret: config.frappeApiSecret,
    });
    return res.data;
  },

  async getPlan(sessionId: string): Promise<any> {
    const res = await axios.get(`${API_BASE}/plan/${sessionId}`);
    return res.data;
  },

  async exportApp(sessionId: string, gitRemote?: string): Promise<any> {
    const res = await axios.post(`${API_BASE}/export/${sessionId}`, {
      output_dir: '/tmp/frappe_exports',
      git_remote: gitRemote || null,
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
};
