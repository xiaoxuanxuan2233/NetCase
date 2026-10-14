import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { NewDiagnosisPage } from './pages/NewDiagnosisPage';
import { HistoryPage } from './pages/HistoryPage';
import { DiagnosisResultPage } from './pages/DiagnosisResultPage';
import { SettingsPage } from './pages/SettingsPage';
import { ComparePage } from './pages/ComparePage';
import { api } from './services/api';
import { emptyDashboard } from './services/example';
import { validateTarget } from './services/format';
import type { DiagnosisRecord, Job, Settings } from './types';

afterEach(() => { cleanup(); vi.restoreAllMocks(); window.location.hash = ''; });

const settings: Settings = { theme: 'light', timeout_seconds: 3, default_mode: 'quick',
  default_modules: ['dns', 'tcp', 'tls'] };
const record: DiagnosisRecord = {
  id: 'test-1', created_at: new Date().toISOString(), target: 'example.com', mode: 'quick',
  status: 'success', duration_ms: 122, summary: '本次已选检测项目均通过。',
  environment: '家庭 Wi-Fi', notes: '', rule_version: 'rules-1', source: 'runtime',
  modules: [{ name: 'dns', status: 'success', duration_ms: 11, detail: '获得 A 记录。',
    evidence: { A: ['93.184.215.14'] }, error_type: null }],
  conclusions: [{ title: '本次检查已通过。', confidence: '确认', level: 'success',
    evidence: ['DNS：获得 A 记录。'], possible_causes: [], next_steps: ['如仍不可用，请检查浏览器。'],
    knowledge: '一次成功只证明这次检测。' }], context: { address_families: ['IPv4'], port: 443 },
};

describe('validation', () => {
  it('rejects credentials, shell-shaped input and invalid schemes', () => {
    expect(() => validateTarget('https://user:password@example.com')).toThrow();
    expect(() => validateTarget('example.com -c 100')).toThrow();
    expect(() => validateTarget('file:///etc/passwd')).toThrow();
    expect(validateTarget('example.com')).toBe('example.com');
  });
});

describe('dashboard', () => {
  it('shows loading, a real empty state, and no fabricated success rate', async () => {
    vi.spyOn(api, 'dashboard').mockResolvedValue(emptyDashboard(7));
    vi.spyOn(api, 'health').mockResolvedValue({ version: '0.1.0', platform: 'Windows', engine_available: true });
    vi.spyOn(api, 'settings').mockResolvedValue(settings);
    render(<App />);
    expect(screen.getByRole('status', { name: '正在读取本地数据' })).toBeInTheDocument();
    await screen.findByText('每一次诊断，都值得留存');
    expect(screen.getByText('完成检测后生成统计')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /看见连接/ })).toBeInTheDocument();
  });

  it('separates a service failure from an empty history', async () => {
    vi.spyOn(api, 'dashboard').mockRejectedValue(new Error('本地服务暂时不可用'));
    vi.spyOn(api, 'health').mockResolvedValue({ version: '0.1.0', platform: 'Windows', engine_available: true });
    vi.spyOn(api, 'settings').mockResolvedValue(settings);
    render(<App />);
    await screen.findByText('还没有连接到本地服务');
    expect(screen.getByText('本地服务暂时不可用')).toBeInTheDocument();
    expect(screen.queryByText('每一次诊断，都值得留存')).not.toBeInTheDocument();
  });
});

describe('diagnosis flow', () => {
  it('validates the target before submitting', async () => {
    vi.spyOn(api, 'settings').mockResolvedValue(settings);
    const start = vi.spyOn(api, 'startDiagnosis').mockResolvedValue({ id: 'job-1', status: 'pending', modules: {} });
    render(<NewDiagnosisPage initialTarget="" onComplete={vi.fn()} onBack={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText('example.com 或 https://example.com'),
      { target: { value: 'https://alice:secret@example.com' } });
    await userEvent.click(screen.getByRole('button', { name: /开始诊断/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('仅支持不含账号密码');
    expect(start).not.toHaveBeenCalled();
  });

  it('submits real parameters, polls progress and opens the stored result', async () => {
    vi.spyOn(api, 'settings').mockResolvedValue(settings);
    const start = vi.spyOn(api, 'startDiagnosis').mockResolvedValue({ id: 'job-1', status: 'pending',
      modules: { dns: 'pending', tcp: 'pending', tls: 'pending' } });
    const job: Job = { id: 'job-1', status: 'completed', current: null, record_id: 'test-1',
      error: null, created_at: record.created_at, modules: { dns: 'success', tcp: 'success', tls: 'success' },
      results: record.modules };
    vi.spyOn(api, 'job').mockResolvedValue(job);
    vi.spyOn(api, 'record').mockResolvedValue(record);
    const done = vi.fn();
    render(<NewDiagnosisPage initialTarget="example.com" onComplete={done} onBack={vi.fn()} />);
    await waitFor(() => expect(screen.getByRole('combobox', { name: /单步超时/ })).toHaveValue('3'));
    await userEvent.click(screen.getByRole('button', { name: /开始诊断/ }));
    await waitFor(() => expect(start).toHaveBeenCalledWith(expect.objectContaining({
      target: 'example.com', mode: 'quick', timeout_seconds: 3, resolver: 'system', allow_local: false,
    })));
    await waitFor(() => expect(done).toHaveBeenCalledWith(record));
  });

  it('saves a validated draft without running a probe', async () => {
    vi.spyOn(api, 'settings').mockResolvedValue(settings);
    const draft = vi.spyOn(api, 'draft').mockResolvedValue(undefined);
    const start = vi.spyOn(api, 'startDiagnosis');
    render(<NewDiagnosisPage initialTarget="example.com" onComplete={vi.fn()} onBack={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: '保存草稿' }));
    await screen.findByText('草稿已保存，可在概览页继续');
    expect(draft).toHaveBeenCalledWith({ target: 'example.com', port: null, mode: 'quick' });
    expect(start).not.toHaveBeenCalled();
  });
});

describe('history and result', () => {
  it('loads history and filters by target', async () => {
    const history = vi.spyOn(api, 'history').mockResolvedValue({ total: 1, items: [record] });
    render(<HistoryPage onOpen={vi.fn()} onCompare={vi.fn()} onChange={vi.fn()} />);
    await screen.findByText('本次已选检测项目均通过。');
    const search = screen.getByRole('textbox', { name: '按域名或地址筛选历史' });
    await userEvent.type(search, 'example');
    await waitFor(() => expect(history).toHaveBeenLastCalledWith(expect.objectContaining({ target: 'example' })),
      { timeout: 1500 });
    expect(screen.getByText('本次已选检测项目均通过。')).toBeInTheDocument();
  });

  it('shows the rule evidence and exports through the redacted API', async () => {
    const report = vi.spyOn(api, 'downloadReport').mockResolvedValue();
    render(<DiagnosisResultPage record={record} onHistory={vi.fn()} onBack={vi.fn()} onUpdated={vi.fn()} />);
    expect(screen.getByText('本次检查已通过。')).toBeInTheDocument();
    expect(screen.getByText('DNS：获得 A 记录。')).toBeInTheDocument();
    await userEvent.click(screen.getByText('DNS'));
    const details = document.querySelector('details.module-result')!;
    expect(within(details as HTMLElement).getByText(/93.184.215.14/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Markdown/ }));
    await waitFor(() => expect(report).toHaveBeenCalledWith('test-1', 'markdown'));
  });
});

describe('settings and comparison', () => {
  it('saves defaults, changes the applied theme and clears local history', async () => {
    vi.spyOn(api, 'settings').mockResolvedValue(settings);
    const save = vi.spyOn(api, 'saveSettings').mockImplementation(async value => value);
    const clear = vi.spyOn(api, 'clearRecords').mockResolvedValue();
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const onTheme = vi.fn();
    const onCleared = vi.fn();
    render(<SettingsPage platform="Windows" onTheme={onTheme} onCleared={onCleared} />);
    await screen.findByText('%LOCALAPPDATA%\\NetCase\\netcase.db');
    await userEvent.click(screen.getByRole('radio', { name: '深色' }));
    await userEvent.selectOptions(screen.getByLabelText(/单步超时时间/), '5');
    await userEvent.click(screen.getByRole('button', { name: /保存设置/ }));
    await waitFor(() => expect(save).toHaveBeenCalledWith(expect.objectContaining({
      theme: 'dark', timeout_seconds: 5,
    })));
    expect(onTheme).toHaveBeenCalledWith('dark');
    await userEvent.click(screen.getByRole('button', { name: '清空历史记录' }));
    expect(confirm).toHaveBeenCalled();
    await waitFor(() => expect(clear).toHaveBeenCalled());
    expect(onCleared).toHaveBeenCalled();
  });

  it('displays condition differences without guessing their cause', async () => {
    const other = { ...record, id: 'test-2', environment: '手机热点',
      created_at: new Date(Date.now() - 60_000).toISOString() };
    vi.spyOn(api, 'compare').mockResolvedValue({
      left: record, right: other,
      conditions_equal: { target: true, network_label: false, resolver: true,
        address_families: true, port: true, modules: true, time: false },
      changes: [], caution: '只描述两次检测的差异。',
    });
    render(<ComparePage left="test-1" right="test-2" onBack={vi.fn()} />);
    expect(await screen.findByText('只描述两次检测的差异。')).toBeInTheDocument();
    expect(screen.getByText('环境：手机热点')).toBeInTheDocument();
  });
});
