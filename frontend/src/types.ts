export type PipelineStage =
  | 'idle'
  | 'discovery'
  | 'drafting'
  | 'validating'
  | 'healing'
  | 'scripting'
  | 'reporting'
  | 'exporting'
  | 'testing'
  | 'done'
  | 'failed';

export interface SubagentActivity {
  agent: string;
  role: string;
  status: 'active' | 'completed' | 'idle' | 'failed';
  action: string;
  timestamp?: string;
}

export interface OptionSpec {
  value: string;
  label: string;
  description?: string | null;
}

export type DiscoveryPhase = 'basics' | 'domain' | 'confirm';

export interface QuestionSpec {
  id: string;
  phase: DiscoveryPhase;
  text: string;
  help?: string | null;
  input: 'single' | 'multi' | 'text' | 'yesno';
  options?: OptionSpec[] | null;
  allow_custom?: boolean;
}

export interface CoverageSpec {
  basics: number;
  domain: number;
}

export interface InterviewTurn {
  kind: 'question' | 'summary' | 'done';
  say: string;
  question?: QuestionSpec | null;
  assumptions: string[];
  coverage: CoverageSpec;
}

export interface QuestionOption {
  label: string;
  value: string;
  description?: string;
}

export interface InterviewQuestion {
  id: string;
  question: string;
  reason?: string;
  options: (string | QuestionOption)[];
  allows_custom?: boolean;
}

export interface FieldSpec {
  fieldname: string;
  label: string;
  fieldtype: string;
  options?: string;
  reqd?: boolean;
  unique?: boolean;
  read_only?: boolean;
  hidden?: boolean;
  in_list_view?: boolean;
  in_standard_filter?: boolean;
  allow_on_submit?: boolean;
  default?: string;
  fetch_from?: string;
  depends_on?: string;
  description?: string;
}

export interface PermissionSpec {
  role: string;
  read: boolean;
  write: boolean;
  create: boolean;
  delete: boolean;
  submit?: boolean;
  cancel?: boolean;
}

export interface DocTypeSpec {
  name: string;
  module: string;
  kind?: string;
  istable?: boolean;
  is_submittable?: boolean;
  is_single?: boolean;
  autoname?: string;
  title_field?: string;
  fields: FieldSpec[];
  permissions: PermissionSpec[];
}

export interface WorkflowState {
  state: string;
  doc_status: 0 | 1 | 2;
  style?: 'Success' | 'Warning' | 'Danger' | 'Primary' | '';
  allow_edit: string;
  update_field?: string | null;
  update_value?: string | null;
}

export interface WorkflowTransition {
  state: string;
  action: string;
  next_state: string;
  allowed: string;
  condition?: string | null;
  allow_self_approval?: 0 | 1;
}

export interface WorkflowSpec {
  name: string;
  document_type: string;
  workflow_state_field?: string;
  is_active?: 0 | 1;
  states: WorkflowState[];
  transitions: WorkflowTransition[];
}

export interface ReportSpec {
  name: string;
  ref_doctype: string;
  report_type: string;
  columns?: any[];
  filters?: any[];
}

export interface AppMetadata {
  app_name: string;
  title: string;
  description?: string;
  publisher?: string;
  email?: string;
  version?: string;
  requires_erpnext?: boolean;
  modules?: string[];
  roles?: string[];
  doctypes: DocTypeSpec[];
  workflows?: WorkflowSpec[];
  reports?: ReportSpec[];
}

export interface AppSpecV2 {
  spec_version: string;
  status: string;
  archetype?: string;
  questions?: InterviewQuestion[];
  assumptions: string[];
  app?: AppMetadata;
}

export interface ValidationReportItem {
  rule: string;
  doctype?: string;
  field?: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface ValidationReport {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  fix_hints: any[];
  detailed_errors?: ValidationReportItem[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  interview_turn?: InterviewTurn;
  answeredAnswer?: string | null;
}

export interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  size?: number;
  children?: FileNode[];
}

export interface Question {
  id: string;
  question: string;
  why_it_matters?: string;
  options?: any[];
  default?: string;
}

export interface BuildResponse {
  session_id: string;
  status: string;
  created: string[];
  errors: string[];
  preview_urls: string[];
  questions?: Question[];
  assumptions?: string[];
  spec?: any;
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
