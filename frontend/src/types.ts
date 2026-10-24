export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface Question {
  id: string;
  question: string;
  why_it_matters?: string;
  options?: string[];
  default?: string;
}

export interface FrappeConfig {
  frappeUrl: string;
  frappeApiKey: string;
  frappeApiSecret: string;
  clientName: string;
  llmBaseUrl?: string;
  llmApiKey?: string;
  llmModel?: string;
}

export type BuildStatus =
  | 'idle'
  | 'discovery'
  | 'needs_input'
  | 'planned'
  | 'applying'
  | 'done'
  | 'partial'
  | 'failed'
  | 'validation_failed';

export interface BuildResponse {
  session_id: string;
  status: BuildStatus;
  created: string[];
  errors: string[];
  preview_urls: string[];
  questions?: Question[];
  assumptions?: string[];
  spec?: any;
}
