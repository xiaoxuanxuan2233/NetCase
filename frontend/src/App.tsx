import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowRight, BookOpen, Box, Check, ChevronDown, ChevronRight,
  CircleHelp, Clock3, Command, Database, FileClock, FlaskConical, LayoutDashboard,
  Menu, Moon, Plus, RefreshCw, Settings2, ShieldCheck, Sun, Terminal, Trash2, Unplug, X } from 'lucide-react';
import { api, downloadJson, isPreview } from './services/api';
import { exampleDashboard } from './services/example';
import { formatDate, modeLabel } from './services/format';
import { useDashboard } from './hooks/useDashboard';
import { Dialog, Logo } from './components/Primitives';
import { TargetForm } from './components/TargetForm';
import { RecordDetail } from './components/RecordDetail';
import { ActivityPanel, EngineNote, ErrorsPanel, FavoritesPanel, KnowledgeStrip, LatestPanel,
  RecentPanel, StatCards } from './components/DashboardPanels';
import { NewDiagnosisPage } from './pages/NewDiagnosisPage';
import { DiagnosisResultPage } from './pages/DiagnosisResultPage';
import { HistoryPage } from './pages/HistoryPage';
import { ComparePage } from './pages/ComparePage';
import { SettingsPage } from './pages/SettingsPage';
import type { DiagnosisRecord, Settings } from './types';

type Modal = { kind: 'favorite' | 'draft'; target: string } | { kind: 'help' | 'drafts' }
  | { kind: 'record'; record: DiagnosisRecord } | null;
type View = 'dashboard' | 'diagnose' | 'result' | 'history' | 'compare' | 'settings';
const validViews: View[] = ['dashboard', 'diagnose', 'result', 'history', 'compare', 'settings'];

function route(): { view: View; id: string | null; pair: [string, string] | null } {
  const raw = window.location.hash.slice(2);
  const [path, query] = raw.split('?');
  const [name, id] = path.split('/');
  const params = new URLSearchParams(query || '');
  return { view: validViews.includes(name as View) ? name as View : 'dashboard',
    id: name === 'result' ? id || null : null,
    pair: name === 'compare' && params.get('left') && params.get('right')
      ? [params.get('left')!, params.get('right')!] : null };
}

function initialTheme(): 'light' | 'dark' {
  try { const saved = localStorage.getItem('netcase.theme'); if (saved === 'dark' || saved === 'light') return saved; }
  catch { /* Optional preference storage must not prevent the dashboard from opening. */ }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export default function App() {
  const [theme, setTheme] = useState(initialTheme);
  const [themeMode, setThemeMode] = useState<Settings['theme']>('system');
  const [days, setDays] = useState(7);
  const [revision, setRevision] = useState(0);
  const [demo, setDemo] = useState(false);
  const [modal, setModal] = useState<Modal>(null);
  const [menu, setMenu] = useState(false);
  const [notice, setNotice] = useState('');
  const [mutating, setMutating] = useState(false);
  const [location, setLocation] = useState(route);
  const [selectedRecord, setSelectedRecord] = useState<DiagnosisRecord | null>(null);
  const [recordError, setRecordError] = useState('');
  const [diagnosticTarget, setDiagnosticTarget] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const state = useDashboard(days, revision);
  const example = useMemo(() => exampleDashboard(days), [days]);
  const data = demo ? example : state.data;

  useEffect(() => { const handler = () => setLocation(route()); window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler); }, []);
  useEffect(() => {
    if (isPreview) return;
    let alive = true;
    api.settings().then(s => {
      if (!alive) return;
      setThemeMode(s.theme);
      setTheme(s.theme === 'system'
        ? (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : s.theme);
    }).catch(() => { /* Health banner displays service availability. */ });
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    if (themeMode !== 'system' || !window.matchMedia) return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () => setTheme(media.matches ? 'dark' : 'light');
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [themeMode]);
  useEffect(() => {
    if (location.view !== 'result' || !location.id || selectedRecord?.id === location.id) return;
    let alive = true;
    // A failed direct link should display an error instead of an endless spinner.
    api.record(location.id).then(record => { if (alive) setSelectedRecord(record); })
      .catch(e => { if (alive) setRecordError(e instanceof Error ? e.message : '记录加载失败'); });
    return () => { alive = false; };
  }, [location.view, location.id, selectedRecord?.id]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('netcase.theme', theme); } catch { /* Theme still applies in memory. */ }
  }, [theme]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(''), 6500);
    return () => clearTimeout(timer);
  }, [notice]);

  function navigate(view: View, suffix = '') {
    setRecordError('');
    setMenu(false); setModal(null); setLocation({ view, id: view === 'result' ? suffix : null,
      pair: view === 'compare' ? route().pair : null });
    window.location.hash = `/${view}${suffix ? `/${suffix}` : ''}`;
    window.scrollTo?.(0, 0);
  }
  function start(target = '') { setDiagnosticTarget(target); setDemo(false); navigate('diagnose'); }
  function openRecord(record: DiagnosisRecord) {
    if (demo) setModal({ kind: 'record', record });
    else { setSelectedRecord(record); navigate('result', record.id); }
  }
  const completed = useCallback((record: DiagnosisRecord) => {
    setSelectedRecord(record); setRevision(v => v + 1);
    setLocation({ view: 'result', id: record.id, pair: null });
    window.location.hash = `/result/${record.id}`;
    window.scrollTo?.(0, 0);
  }, []);
  function compare(left: string, right: string) {
    const next = `#/compare?left=${encodeURIComponent(left)}&right=${encodeURIComponent(right)}`;
    window.location.hash = next;
    setLocation({ view: 'compare', id: null, pair: [left, right] });
    window.scrollTo?.(0, 0);
  }
  async function changeTheme(value: Settings['theme']) {
    setThemeMode(value);
    const effective = value === 'system' ? (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : value;
    setTheme(effective);
    try { const current = await api.settings(); await api.saveSettings({ ...current, theme: value }); }
    catch (e) { setNotice(e instanceof Error ? e.message : '主题仅在当前浏览器生效，设置保存失败'); }
  }
  function showHelp() { setMenu(false); setModal({ kind: 'help' }); }
  function changeDemo() { setModal(null); setDemo(d => !d); navigate('dashboard'); }
  async function mutate(action: () => Promise<unknown>, message: string) {
    if (mutating) return;
    setMutating(true);
    try { await action(); setRevision(v => v + 1); setNotice(message); }
    catch (e) { setNotice(e instanceof Error ? e.message : '操作失败，请重试'); }
    finally { setMutating(false); }
  }
  async function importFile(file: File | undefined) {
    if (!file) return;
    try { const result = await api.importFile(file); setRevision(v => v + 1);
      setNotice(`已导入 ${result.imported} 条记录，跳过 ${result.skipped} 条重复记录`); }
    catch (e) { setNotice(e instanceof Error ? e.message : '导入失败'); }
  }
  async function exportAll() {
    try { downloadJson(await api.exportRecords(), 'netcase-records.json'); }
    catch (e) { setNotice(e instanceof Error ? e.message : '导出失败'); }
  }

  return <div className="app-shell">
    <a className="skip-link" href="#main">跳转到主要内容</a>
    {menu && <button className="sidebar-backdrop" aria-label="关闭导航" onClick={() => setMenu(false)} />}
    <aside className={`sidebar ${menu ? 'open' : ''}`} aria-label="主导航">
      <Logo /><div className="workspace-switch"><span className="workspace-avatar"><Terminal size={17} /></span>
        <span><strong>个人工作空间</strong><small>LOCAL WORKSPACE</small></span><span className="local-indicator" /></div>
      <div className="nav-caption">工作台</div>
      <nav><button className={`nav-item ${location.view === 'dashboard' ? 'active' : ''}`}
          aria-current={location.view === 'dashboard' ? 'page' : undefined} onClick={() => navigate('dashboard')}>
          <LayoutDashboard size={18} />概览{location.view === 'dashboard' && <span className="nav-active-dot" />}</button>
        <button className={`nav-item ${location.view === 'diagnose' ? 'active' : ''}`}
          aria-current={location.view === 'diagnose' ? 'page' : undefined} onClick={() => start()}><Plus size={18} />新建诊断</button>
        <button className={`nav-item ${['history', 'result', 'compare'].includes(location.view) ? 'active' : ''}`}
          aria-current={location.view === 'history' ? 'page' : undefined} onClick={() => navigate('history')}>
          <Clock3 size={18} />历史记录</button>
        <button className={`nav-item ${location.view === 'settings' ? 'active' : ''}`}
          aria-current={location.view === 'settings' ? 'page' : undefined} onClick={() => navigate('settings')}>
          <Settings2 size={18} />设置</button>
      </nav>
      <div className="sidebar-insight"><div className="insight-grid" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /><span /><span /></div>
        <p>Understand your network,<br /><strong>not just test it.</strong></p><span>让每一次连接都有迹可循。</span></div>
      <div className="sidebar-bottom"><button className={`nav-item ${demo ? 'demo-active' : ''}`} onClick={changeDemo}>
        <FlaskConical size={17} />{demo ? '返回我的数据' : '探索示例视图'}<ArrowRight size={14} /></button>
        <button className="nav-item" onClick={showHelp}><BookOpen size={17} />使用指南<span className="nav-mini">v0.1</span></button>
        <div className="sidebar-footer"><span><span className="tiny-dot green" />Local-first. Always.</span>
          <button className="theme-toggle" aria-label={`切换到${theme === 'light' ? '深色' : '浅色'}主题`}
            onClick={() => void changeTheme(theme === 'light' ? 'dark' : 'light')}>{theme === 'light' ? <Moon size={17} /> : <Sun size={17} />}</button>
        </div></div>
    </aside>

    <div className="main-shell"><header className="topbar">
      <div className="breadcrumb"><button className="icon-button mobile-menu" aria-label="打开导航" onClick={() => setMenu(true)}><Menu size={20} /></button>
        <Box size={15} /><span>工作空间</span><ChevronRight size={13} /><strong>{({ dashboard: '概览', diagnose: '新建诊断', result: '诊断结果', history: '历史记录', compare: '诊断对比', settings: '设置' } as Record<View, string>)[location.view]}</strong></div>
      <div className="topbar-right"><span className={`connection-state ${state.error ? 'offline' : ''}`}>
        <span className={`tiny-dot ${state.error ? 'orange' : state.loading ? 'neutral' : 'green'}`} />
        {isPreview ? '独立界面预览' : state.loading ? '连接本地服务…' : state.error ? '本地服务未连接' : '本地服务已连接'}</span>
        <span className="topbar-divider" /><button className="icon-button" aria-label="帮助与版本说明" onClick={showHelp}><CircleHelp size={18} /></button>
        <span className="user-avatar" title="本地个人工作空间">N</span></div>
    </header>
    <main id="main" className="main-content">
      {location.view === 'dashboard' ? <>
      <div className="page-heading"><div><div className="eyebrow page-eyebrow">YOUR NETWORK, EXPLAINED.</div>
        <h1>网络概览<span className="version-badge">BETA</span></h1><p>看见网络的每一层，让排查有据可依。</p></div>
        <div className="heading-actions"><button className={`button secondary refresh-button ${state.loading ? 'loading' : ''}`}
          aria-label="刷新本地数据" onClick={() => setRevision(v => v + 1)} disabled={state.loading || demo}><RefreshCw size={16} /></button>
          <button className="button primary" onClick={() => start()}><Plus size={17} />新建诊断</button></div></div>

      {demo && <div className="demo-banner"><FlaskConical size={17} /><p><strong>示例视图</strong>所有数值均为界面示例，不代表你的网络状况。</p>
        <button onClick={changeDemo}>返回我的数据<X size={14} /></button></div>}
      {isPreview && !demo && <div className="preview-banner"><InfoIcon /><p>当前是可交互的首页预览。收藏与草稿保存在浏览器中；完整本地版使用 SQLite。</p></div>}

      <div className="section-toolbar"><span><span className="tiny-dot neutral" />{demo ? '示例工作空间' : '我的网络工作台'}</span>
        <div><label className="range-select"><Clock3 size={13} /><select value={days} aria-label="统计时间范围" onChange={e => setDays(Number(e.target.value))}>
          <option value={7}>最近 7 天</option><option value={30}>最近 30 天</option><option value={1}>今天</option>
        </select><ChevronDown size={13} /></label><span className="timezone-label">{Intl.DateTimeFormat().resolvedOptions().timeZone}</span></div></div>

      {!demo && state.error ? <section className="service-error panel" role="alert"><Unplug size={34} /><h2>还没有连接到本地服务</h2>
        <p>请启动 NetCase 后端后重试。连接失败不会被当作“没有历史记录”。</p>
        <code>{state.error}</code><div><button className="button primary" onClick={() => setRevision(v => v + 1)}><RefreshCw size={15} />重新连接</button>
          <button className="button secondary" onClick={changeDemo}>浏览示例视图<ArrowRight size={15} /></button></div>
        <button className="text-button" onClick={showHelp}>查看本地启动说明</button></section>
        : data ? <div aria-busy={state.loading && !demo} className={state.loading && !demo ? 'refreshing' : ''}>
          <StatCards data={data} />
          <div className="dashboard-columns"><div className="main-column">
            <LatestPanel record={data.latest} onStart={() => start()} onDemo={() => setDemo(true)} onOpen={openRecord} />
            <RecentPanel data={data} onOpen={openRecord} onImport={() => input.current?.click()}
              onExport={exportAll} canTransfer={!demo && !isPreview && !state.error && !mutating} />
            <KnowledgeStrip onLearn={showHelp} />
          </div><div className="side-column">
            <ActivityPanel data={data} />
            <FavoritesPanel data={data} onAdd={() => setModal({ kind: 'favorite', target: '' })} onStart={start}
              onRemove={id => mutate(() => api.remove('favorites', id), '已取消收藏')} readOnly={demo || mutating} />
            <ErrorsPanel data={data} />
            {!demo && data.drafts.length > 0 && <button className="drafts-link" onClick={() => setModal({ kind: 'drafts' })}>
              <FileClock size={17} /><span>{data.drafts.length} 个待用检测草稿</span><ChevronRight size={15} /></button>}
          </div></div>
        </div> : <div className="skeleton-layout" role="status" aria-label="正在读取本地数据"><div /><div /><div /><div /><section /><section /></div>}
      </> : location.view === 'diagnose' ? <NewDiagnosisPage initialTarget={diagnosticTarget}
        onBack={() => navigate('dashboard')} onComplete={completed} />
        : location.view === 'result' ? selectedRecord && selectedRecord.id === location.id
          ? <DiagnosisResultPage key={selectedRecord.id} record={selectedRecord} onUpdated={record => { setSelectedRecord(record); setRevision(v => v + 1); }}
            onBack={() => navigate('history')} onHistory={() => navigate('history')} />
          : <div className="panel history-empty">{recordError ? <p role="alert">{recordError}</p> : '正在加载诊断记录…'}<button className="text-button" onClick={() => navigate('history')}>返回历史</button></div>
        : location.view === 'history' ? <HistoryPage onOpen={openRecord} onCompare={compare}
          onChange={() => setRevision(v => v + 1)} />
        : location.view === 'compare' && location.pair ? <ComparePage left={location.pair[0]}
          right={location.pair[1]} onBack={() => navigate('history')} />
        : location.view === 'settings' ? <SettingsPage platform={state.health?.platform || ''}
          onTheme={value => { setThemeMode(value); setTheme(value === 'system'
            ? (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : value); }}
          onCleared={() => setRevision(v => v + 1)} />
        : <div className="panel history-empty"><p>请选择两条记录进行比较。</p><button className="button primary" onClick={() => navigate('history')}>打开历史记录</button></div>}
      <footer className="page-footer"><EngineNote /><span><ShieldCheck size={13} />没有自动探测 · 没有遥测</span></footer>
    </main></div>
    <input className="sr-only" type="file" ref={input} accept=".json,application/json" aria-label="导入 NetCase 报告"
      onChange={e => { void importFile(e.target.files?.[0]); e.target.value = ''; }} />

    {modal?.kind === 'favorite' || modal?.kind === 'draft' ? <TargetForm kind={modal.kind} initial={modal.target}
      onClose={() => setModal(null)} onSaved={() => { setNotice(modal.kind === 'favorite' ? '目标已收藏' : '检测草稿已保存；尚未执行检测'); setModal(null); setRevision(v => v + 1); }} /> : null}
    {modal?.kind === 'record' && <RecordDetail record={modal.record} demo={demo} onClose={() => setModal(null)} />}
    {modal?.kind === 'drafts' && <Dialog title="检测草稿" eyebrow="DRAFTS · 尚未执行" onClose={() => setModal(null)}>
      <p className="dialog-description">草稿不会计入诊断统计。选择目标后可以继续编辑并启动真实检测。</p>
      <div className="draft-list">{state.data?.drafts.length ? state.data.drafts.map(d => <div key={d.id}>
        <FileClock size={20} /><span><strong className="mono">{d.target}</strong><small>{modeLabel[d.mode]} · {d.port ? `端口 ${d.port}` : '默认端口'} · {formatDate(d.created_at)}</small></span>
        <button className="text-button" onClick={() => start(d.target)}>继续</button>
        <button disabled={mutating} className="icon-button" aria-label={`移除草稿 ${d.target}`}
          onClick={() => mutate(() => api.remove('drafts', d.id), '草稿已移除')}><Trash2 size={16} /></button></div>) : <p>暂无待用草稿。</p>}</div>
    </Dialog>}
    {modal?.kind === 'help' && <Dialog title="从观察开始，理解你的网络" eyebrow="NETCASE · GETTING STARTED" onClose={() => setModal(null)} wide>
      <p className="dialog-description">NetCase — Understand your network, not just test it.</p>
      <div className="help-section"><h3><Check size={17} />当前版本：NetCase v0.1</h3>
        <p>提供 DNS、TCP、TLS、HTTP、Ping 和路由追踪的单目标诊断、规则解释、SQLite 历史、两次对比、报告导出及设置。</p>
        <p>初次启动不填充示例。示例视图仅用来了解界面，不进入历史和统计。</p></div>
      <div className="help-section"><h3><Command size={17} />Windows 本地启动</h3>
        <p>安装 Python 3.12+、Node.js 22.12+（推荐受支持的 LTS）和 uv 后，在项目根目录运行：</p>
        <pre>powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1</pre>
        <p>浏览器打开 <code>http://127.0.0.1:8000</code>。完整说明见源码包 README。</p></div>
      <div className="help-section"><h3><Database size={17} />数据属于你</h3>
        <p>{isPreview ? '独立预览只在当前浏览器保存收藏、草稿和主题，不连接后端。'
          : 'Windows 数据默认位于 %LOCALAPPDATA%/NetCase/netcase.db，可通过 NETCASE_DATA_DIR 修改。'}报告可能包含内网地址与备注，分享前请自行检查。</p>
        <p>导入的记录会明确标注来源。统计根据所选日期范围计算；通过率排除完全无法检测的记录。诊断总耗时不能用来替代网络延迟。</p></div>
      <div className="help-section"><h3><ShieldCheck size={17} />每一个判断，都需要证据</h3>
        <ul><li>DNS 结果不同，可能来自 CDN、负载均衡或地理调度。</li>
          <li>TCP 失败不能直接证明防火墙封锁；TLS 失败不能直接证明中间人攻击。</li>
          <li>HTTP 403、429、500 或 503 需要结合网站服务与访问条件解释。</li>
          <li>网络环境、IP 协议和测试时间不同，会影响检测结果。</li></ul></div>
    </Dialog>}
    {notice && <div className="toast" role="status"><span>{notice}</span><button className="icon-button" onClick={() => setNotice('')} aria-label="关闭提示"><X size={16} /></button></div>}
  </div>;
}

function InfoIcon() { return <CircleHelp size={16} />; }
