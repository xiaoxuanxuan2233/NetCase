import { useEffect, useState, type FormEvent } from 'react';
import { Activity, ArrowRight, ChevronRight, CircleHelp, Clock3, Database, Globe2,
  Info, Link2, LockKeyhole, Radio, Route, ShieldCheck, Wifi } from 'lucide-react';
import { api, isPreview } from '../services/api';
import { validateTarget, formatDuration } from '../services/format';
import type { DiagnosisInput, DiagnosisRecord, Job, ModuleName, Mode, Status } from '../types';
import { StatusPill } from '../components/Primitives';

const MODULES: { key: ModuleName; name: string; caption: string; icon: typeof Database }[] = [
  { key: 'dns', name: 'DNS 解析', caption: 'A · AAAA · CNAME', icon: Database },
  { key: 'tcp', name: 'TCP 连接', caption: '端口 · IPv4 / IPv6', icon: Link2 },
  { key: 'tls', name: 'HTTPS / TLS', caption: '握手 · 证书校验', icon: LockKeyhole },
  { key: 'http', name: 'HTTP 请求', caption: '状态码 · 重定向', icon: Globe2 },
  { key: 'ping', name: 'ICMP Ping', caption: '延迟 · 丢包', icon: Radio },
  { key: 'traceroute', name: '路由追踪', caption: '最多 16 跳', icon: Route },
];
export function NewDiagnosisPage({ initialTarget, onComplete, onBack }: {
  initialTarget: string; onComplete: (record: DiagnosisRecord) => void; onBack: () => void;
}) {
  const [target, setTarget] = useState(initialTarget);
  const [port, setPort] = useState('');
  const [mode, setMode] = useState<Mode>('quick');
  const [selected, setSelected] = useState<ModuleName[]>(['dns', 'tcp', 'tls']);
  const [timeout, setTimeoutValue] = useState(3);
  const [resolver, setResolver] = useState<DiagnosisInput['resolver']>('system');
  const [comparison, setComparison] = useState<DiagnosisInput['compare_resolver']>(null);
  const [network, setNetwork] = useState('');
  const [local, setLocal] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let active = true;
    api.settings().then(s => {
      if (active) { setMode(s.default_mode); setSelected(s.default_modules);
        setTimeoutValue(s.timeout_seconds); }
    }).catch(() => { /* The inline form can use safe defaults if settings cannot load. */ });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await api.job(jobId!);
        if (stopped) return;
        setJob(next);
        if (next.status === 'completed' && next.record_id) {
          const record = await api.record(next.record_id);
          if (!stopped) onComplete(record);
          return;
        }
        if (next.status === 'failed') { setError(next.error || '诊断任务失败'); return; }
      } catch (e) { if (!stopped) setError(e instanceof Error ? e.message : '无法读取诊断进度'); return; }
      timer = setTimeout(poll, 700);
    }
    void poll();
    return () => { stopped = true; clearTimeout(timer); };
  }, [jobId, onComplete]);

  const modules: ModuleName[] = mode === 'quick' ? ['dns', 'tcp', 'tls']
    : mode === 'full' ? MODULES.map(m => m.key) : selected;
  async function start(e: FormEvent) {
    e.preventDefault(); setError('');
    try {
      const value = validateTarget(target);
      const number = port ? Number(port) : null;
      if (number !== null && (!Number.isInteger(number) || number < 1 || number > 65535)) {
        throw new Error('端口必须是 1–65535 之间的整数');
      }
      if (mode === 'custom' && !selected.length) throw new Error('至少选择一个检测模块');
      setBusy(true);
      const body: DiagnosisInput = { target: value, port: number, mode,
        ...(mode === 'custom' ? { modules: selected } : {}), timeout_seconds: timeout,
        resolver, compare_resolver: comparison === resolver ? null : comparison,
        network_label: network.trim(), allow_local: local };
      const created = await api.startDiagnosis(body);
      setJobId(created.id);
      setJob({ id: created.id, status: 'pending', current: null,
        modules: created.modules, results: [], record_id: null, error: null,
        created_at: new Date().toISOString() });
    } catch (e) { setError(e instanceof Error ? e.message : '无法开始诊断'); }
    finally { setBusy(false); }
  }
  function toggle(module: ModuleName) {
    setSelected(current => current.includes(module)
      ? current.filter(item => item !== module) : [...current, module]);
  }
  async function saveDraft() {
    setError(''); setNotice('');
    try {
      const value = validateTarget(target);
      const number = port ? Number(port) : null;
      if (number !== null && (!Number.isInteger(number) || number < 1 || number > 65535)) {
        throw new Error('端口必须是 1–65535 之间的整数');
      }
      setBusy(true);
      await api.draft({ target: value, port: number, mode: mode === 'full' ? 'full' : 'quick' });
      setNotice('草稿已保存，可在概览页继续');
    } catch (e) { setError(e instanceof Error ? e.message : '草稿保存失败'); }
    finally { setBusy(false); }
  }

  return <div className="interior-page diagnosis-page"><div className="interior-heading"><div>
    <div className="eyebrow">START WITH EVIDENCE</div><h1>新建诊断</h1>
    <p>输入一个目标，让每一层连接都留下清晰的证据。</p></div>
    <button className="text-button muted" onClick={onBack}>返回概览<ChevronRight size={14} /></button></div>
    {isPreview && <div className="preview-banner"><Info size={16} />独立预览无法执行真实探测，请启动本地版。</div>}
    <div className="diagnosis-layout"><form className="panel diagnostic-form" onSubmit={start}>
      <div className="panel-heading"><h2><span className="section-dot" />检测目标与配置</h2>
        <span className="small muted">单个目标 · 本机执行</span></div>
      <div className="form-body"><label className="field-label">目标域名、IP 或 URL
        <div className="input-frame"><Globe2 size={18} /><input required value={target} onChange={e => setTarget(e.target.value)}
          placeholder="example.com 或 https://example.com" maxLength={2048} spellCheck={false}
          autoComplete="off" disabled={Boolean(jobId && job?.status !== 'failed')} autoFocus /></div></label>
        <div className="field-grid"><label className="field-label">端口 <span className="muted">可选</span>
          <input className="plain-input" type="number" min={1} max={65535} step={1}
            value={port} onChange={e => setPort(e.target.value)} placeholder="按协议选择" disabled={Boolean(jobId)} /></label>
          <label className="field-label">单步超时
            <select className="plain-input" value={timeout} onChange={e => setTimeoutValue(Number(e.target.value))} disabled={Boolean(jobId)}>
              {[1, 2, 3, 5, 8, 10].map(v => <option key={v} value={v}>{v} 秒</option>)}</select></label></div>
        <div className="field-label">检测模式</div><div className="diagnosis-modes">
          {(['quick', 'full', 'custom'] as Mode[]).map(value => <label key={value} className={mode === value ? 'chosen' : ''}>
            <input type="radio" name="diagnosis-mode" checked={mode === value} disabled={Boolean(jobId)}
              onChange={() => setMode(value)} /><span><strong>{value === 'quick' ? '快速检查' : value === 'full' ? '完整诊断' : '自定义'}</strong>
              <small>{value === 'quick' ? 'DNS + TCP + TLS' : value === 'full' ? '所有适用模块' : '只运行选择的项目'}</small></span>
          </label>)}</div>
        <div className="module-title">检测项目<span>{mode === 'custom' ? '选择至少 1 项' : '由模式决定'}</span></div>
        <div className="module-select">{MODULES.map(({ key, name, caption, icon: Icon }) => <label key={key}
          className={modules.includes(key) ? 'on' : ''}><input type="checkbox" checked={modules.includes(key)}
            disabled={mode !== 'custom' || Boolean(jobId)} onChange={() => toggle(key)} /><span className="module-icon"><Icon size={17} /></span>
            <span><strong>{name}</strong><small>{caption}</small></span></label>)}</div>
        <div className="form-rule" />
        <div className="field-grid"><label className="field-label">主 DNS 解析器
          <select className="plain-input" value={resolver} onChange={e => setResolver(e.target.value as DiagnosisInput['resolver'])} disabled={Boolean(jobId)}>
            <option value="system">本机系统 DNS（默认）</option><option value="cloudflare">Cloudflare · 1.1.1.1</option>
            <option value="google">Google · 8.8.8.8</option></select></label>
          <label className="field-label">可选对比解析器
            <select className="plain-input" value={comparison ?? ''} onChange={e => setComparison((e.target.value || null) as DiagnosisInput['compare_resolver'])} disabled={Boolean(jobId)}>
              <option value="">不对比（默认）</option><option value="cloudflare">Cloudflare</option><option value="google">Google</option></select></label></div>
        <p className="form-hint"><CircleHelp size={14} />只有主动选用公开解析器时，域名才会发送给该第三方。</p>
        <label className="field-label">网络环境备注 <span className="muted">可选</span>
          <input className="plain-input" maxLength={60} value={network} onChange={e => setNetwork(e.target.value)}
            placeholder="例如：宿舍 Wi-Fi / 手机热点" disabled={Boolean(jobId)} /></label>
        <label className="consent-row"><input type="checkbox" checked={local} onChange={e => setLocal(e.target.checked)} disabled={Boolean(jobId)} />
          <span>允许检测我明确输入的本地网络目标<small>默认禁止访问回环、私网及其他特殊地址；仅用于你有权诊断的设备。</small></span></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        {notice && <p className="inline-notice" role="status">{notice}</p>}
        <div className="form-bottom"><button className="button primary" type="submit" disabled={busy || (jobId !== null && job?.status !== 'failed')}>
          <Activity size={17} />{busy ? '正在建立任务…' : jobId && job?.status !== 'failed' ? '正在诊断' : '开始诊断'}<ArrowRight size={15} /></button>
          {mode !== 'custom' && <button type="button" className="text-button" disabled={busy || Boolean(jobId)} onClick={() => void saveDraft()}>保存草稿</button>}
          {job?.status === 'failed' && <button type="button" className="text-button" onClick={() => { setJobId(null); setJob(null); setError(''); }}>修改后重试</button>}
          <span><ShieldCheck size={15} />本机执行 · 有限时长</span></div>
      </div></form>
      <div className="diagnostic-aside"><section className="panel progress-panel"><div className="panel-heading"><h2>检测进度</h2>
        <span className="small muted">{job?.status === 'completed' ? '已完成' : jobId ? '进行中' : '准备就绪'}</span></div>
        <div className="progress-list">{MODULES.filter(m => modules.includes(m.key) || job?.modules[m.key]).map(({ key, name, icon: Icon }, index) => {
          const state = job?.modules[key] ?? 'pending';
          const result = job?.results.find(m => m.name === key);
          return <div className={`progress-step ${state}`} key={key}><span className="progress-index">{String(index + 1).padStart(2, '0')}</span>
            <span className="progress-icon"><Icon size={17} /></span><div><strong>{name}</strong><small>{result?.detail || (state === 'running' ? '正在检测…' : jobId ? '等待上一项完成' : '等待开始')}</small></div>
            {state === 'pending' || state === 'running' ? <span className={`progress-state ${state}`}>{state === 'running' ? '运行中' : '待检测'}</span>
              : <StatusPill status={state as Status} />}</div>;
        })}</div>
        <div className="progress-foot"><Clock3 size={15} />最长 90 秒，状态以本机实际结果为准。</div></section>
        <div className="aside-tip"><Wifi size={18} /><h3>从哪里开始排查？</h3><p>DNS 找到地址；TCP 建立连接；TLS 验证安全连接；HTTP 返回应用层响应。每一层都可能给出不同的线索。</p>
          {job?.results.length ? <div className="latest-timing"><span>已完成模块</span><strong>{job.results.length} 项</strong><span>最新耗时</span><strong>{formatDuration(job.results.at(-1)?.duration_ms ?? null)}</strong></div>
            : <div className="tip-foot"><Database size={14} />检测前不会产生统计数据</div>}</div>
      </div></div>
  </div>;
}
