import type { Comparison, DashboardData, DiagnosisInput, DiagnosisRecord, Draft, Favorite,
  Health, Job, RecordPage, Settings } from '../types';
import { emptyDashboard } from './example';

declare global { interface Window { __NETCASE_PREVIEW__?: boolean } }
export const isPreview = window.__NETCASE_PREVIEW__ === true;
const previewKey = 'netcase.preview.v1';
const previewSettingsKey = 'netcase.preview.settings.v1';
const defaultSettings: Settings = { timeout_seconds: 3, default_mode: 'quick',
  default_modules: ['dns', 'tcp', 'tls'], theme: 'system' };

function previewState(): { favorites: Favorite[]; drafts: Draft[] } {
  const stored = localStorage.getItem(previewKey);
  if (!stored) return { favorites: [], drafts: [] };
  const value = JSON.parse(stored);
  if (!Array.isArray(value.favorites) || !Array.isArray(value.drafts)) {
    throw new Error('预览数据格式损坏，请清除此文件的本地存储后重试');
  }
  return value;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(10_000);
  const response = await fetch(`/api${path}`, {
    ...init,
    signal: init.signal ? AbortSignal.any([init.signal, timeout]) : timeout,
    headers: { 'Content-Type': 'application/json', 'X-NetCase-Client': 'dashboard', ...init.headers },
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    const detail = typeof problem.detail === 'string' ? problem.detail
      : Array.isArray(problem.detail) ? problem.detail.map((p: { msg: string }) => p.msg).join('；')
      : `请求失败（${response.status}）`;
    throw new Error(detail);
  }
  return response.status === 204 ? undefined as T : response.json();
}

export const api = {
  health(signal?: AbortSignal): Promise<Health> {
    return isPreview ? Promise.resolve({ version: '0.1.0', platform: '浏览器预览', engine_available: false })
      : request('/health', { signal });
  },
  dashboard(days: number, signal?: AbortSignal): Promise<DashboardData> {
    if (isPreview) return Promise.resolve({ ...emptyDashboard(days), ...previewState() });
    return request(`/dashboard?days=${days}&offset=${-new Date().getTimezoneOffset()}`, { signal });
  },
  async favorite(target: string, label: string) {
    if (!isPreview) return request('/favorites', { method: 'POST', body: JSON.stringify({ target, label }) });
    const state = previewState();
    if (state.favorites.some(f => f.target.toLowerCase() === target.toLowerCase())) throw new Error('此目标已收藏');
    if (state.favorites.length >= 100) throw new Error('最多保存 100 个常用目标');
    state.favorites.push({ id: crypto.randomUUID(), target, label });
    localStorage.setItem(previewKey, JSON.stringify(state));
  },
  async remove(kind: 'favorites' | 'drafts', id: string) {
    if (!isPreview) return request(`/${kind}/${encodeURIComponent(id)}`, { method: 'DELETE' });
    const state = previewState();
    if (kind === 'favorites') state.favorites = state.favorites.filter(f => f.id !== id);
    else state.drafts = state.drafts.filter(d => d.id !== id);
    localStorage.setItem(previewKey, JSON.stringify(state));
  },
  async draft(input: Pick<Draft, 'target' | 'port' | 'mode'>) {
    if (!isPreview) return request('/drafts', { method: 'POST', body: JSON.stringify(input) });
    const state = previewState();
    if (state.drafts.length >= 20) throw new Error('最多保存 20 个检测草稿');
    state.drafts.unshift({ ...input, id: crypto.randomUUID(), created_at: new Date().toISOString() });
    localStorage.setItem(previewKey, JSON.stringify(state));
  },
  async importFile(file: File): Promise<{ imported: number; skipped: number }> {
    if (isPreview) throw new Error('报告导入需要启动本地版 NetCase');
    if (file.size > 2 * 1024 * 1024) throw new Error('文件不能超过 2 MiB');
    const body = await file.text();
    try { JSON.parse(body); } catch { throw new Error('请选择有效的 JSON 报告'); }
    return request('/records/import', { method: 'POST', body });
  },
  exportRecords() { return request<{ schema_version: 1; records: unknown[] }>('/records/export'); },
  async settings(): Promise<Settings> {
    return isPreview ? { ...defaultSettings, ...JSON.parse(localStorage.getItem(previewSettingsKey) || '{}') }
      : request('/settings');
  },
  async saveSettings(value: Settings): Promise<Settings> {
    if (isPreview) { localStorage.setItem(previewSettingsKey, JSON.stringify(value)); return value; }
    return request('/settings', { method: 'PUT', body: JSON.stringify(value) });
  },
  startDiagnosis(input: DiagnosisInput): Promise<{ id: string; status: string; modules: Job['modules'] }> {
    if (isPreview) return Promise.reject(new Error('请在本地启动完整版 NetCase 后执行真实诊断'));
    return request('/diagnoses', { method: 'POST', body: JSON.stringify(input) });
  },
  job(id: string): Promise<Job> { return request(`/diagnoses/${encodeURIComponent(id)}`); },
  record(id: string): Promise<DiagnosisRecord> { return request(`/records/${encodeURIComponent(id)}`); },
  history(params: { target?: string; since?: string; until?: string; limit?: number; offset?: number } = {}): Promise<RecordPage> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== '') query.set(key, String(value));
    return request(`/records?${query}`);
  },
  compare(left: string, right: string): Promise<Comparison> {
    return request(`/records/compare?left=${encodeURIComponent(left)}&right=${encodeURIComponent(right)}`);
  },
  removeRecord(id: string) { return request<void>(`/records/${encodeURIComponent(id)}`, { method: 'DELETE' }); },
  clearRecords(before?: string) { return request<void>(`/records${before ? `?before=${encodeURIComponent(before)}` : ''}`, { method: 'DELETE' }); },
  saveNote(id: string, notes: string) { return request<DiagnosisRecord>(`/records/${encodeURIComponent(id)}`,
    { method: 'PATCH', body: JSON.stringify({ notes }) }); },
  async downloadReport(id: string, format: 'json' | 'markdown' | 'html') {
    if (isPreview) throw new Error('请在本地版导出真实诊断报告');
    const response = await fetch(`/api/records/${encodeURIComponent(id)}/report?format=${format}`,
      { headers: { 'X-NetCase-Client': 'dashboard' } });
    if (!response.ok) throw new Error('报告导出失败');
    const type = { json: 'application/json', markdown: 'text/markdown', html: 'text/html' }[format];
    downloadBlob(await response.text(), `netcase-${id}.${format === 'markdown' ? 'md' : format}`, type);
  },
};

export function downloadJson(value: unknown, filename: string) {
  downloadBlob(JSON.stringify(value, null, 2), filename, 'application/json');
}

function downloadBlob(value: string, filename: string, type: string) {
  const url = URL.createObjectURL(new Blob([value], { type }));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
