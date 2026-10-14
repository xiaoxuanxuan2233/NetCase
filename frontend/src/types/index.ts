export type Status = 'success' | 'warning' | 'failed' | 'unsupported';
export type ModuleName = 'dns' | 'tcp' | 'tls' | 'http' | 'ping' | 'traceroute';
export type Mode = 'quick' | 'full' | 'custom';
export interface ModuleResult {
  name: ModuleName;
  status: Status;
  duration_ms: number | null;
  error_type: string | null;
  detail: string;
  evidence: Record<string, unknown>;
}
export interface DiagnosisRecord {
  id: string;
  created_at: string;
  target: string;
  mode: Mode;
  status: Status;
  duration_ms: number;
  summary: string;
  rule_version: string;
  environment: string;
  notes: string;
  modules: ModuleResult[];
  conclusions?: Conclusion[];
  context?: Record<string, unknown>;
  source: 'imported' | 'runtime';
}
export interface Conclusion {
  level: 'info' | 'success' | 'warning' | 'error';
  confidence: '确认' | '较可能' | '无法判断';
  title: string;
  evidence: string[];
  possible_causes: string[];
  next_steps: string[];
  knowledge: string;
}
export interface DiagnosisInput {
  target: string; port: number | null; mode: Mode; modules?: ModuleName[];
  timeout_seconds: number; resolver: 'system' | 'cloudflare' | 'google';
  compare_resolver: 'cloudflare' | 'google' | null;
  network_label: string; allow_local: boolean;
}
export interface Job {
  id: string; status: 'pending' | 'running' | 'completed' | 'failed';
  current: ModuleName | null; modules: Partial<Record<ModuleName, 'pending' | 'running' | Status>>;
  results: ModuleResult[]; record_id: string | null; error: string | null; created_at: string;
}
export interface Settings {
  timeout_seconds: number; default_mode: Mode; default_modules: ModuleName[];
  theme: 'system' | 'light' | 'dark';
}
export interface RecordPage { total: number; items: DiagnosisRecord[] }
export interface Comparison {
  left: DiagnosisRecord; right: DiagnosisRecord;
  conditions_equal: Record<string, boolean>;
  changes: { module: ModuleName; before: ModuleResult; after: ModuleResult; duration_delta_ms: number | null }[];
  caution: string;
}
export interface Favorite { id: string; target: string; label: string }
export interface Draft {
  id: string;
  target: string;
  mode: 'quick' | 'full';
  port: number | null;
  created_at: string;
}
export interface DashboardData {
  days: number;
  timezone_offset_minutes: number;
  stats: { total: number; passed: number; eligible: number; issues: number; median_duration_ms: number | null };
  activity: { date: string; count: number }[];
  errors: { type: string; count: number }[];
  latest: DiagnosisRecord | null;
  recent: DiagnosisRecord[];
  favorites: Favorite[];
  drafts: Draft[];
}
export interface Health { version: string; platform: string; engine_available: boolean }
