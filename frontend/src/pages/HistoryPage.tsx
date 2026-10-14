import { useEffect, useState } from 'react';
import { ArrowLeftRight, ArrowRight, CalendarDays, ChevronLeft, ChevronRight, Clock3,
  Download, Search, Trash2 } from 'lucide-react';
import { api, downloadJson } from '../services/api';
import { formatDate, formatDuration, modeLabel } from '../services/format';
import type { DiagnosisRecord, RecordPage } from '../types';
import { StatusPill } from '../components/Primitives';

export function HistoryPage({ onOpen, onCompare, onChange }: {
  onOpen: (record: DiagnosisRecord) => void; onCompare: (a: string, b: string) => void;
  onChange: () => void;
}) {
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<RecordPage | null>(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => { const timer = setTimeout(() => { setQuery(search); setPage(0); }, 300); return () => clearTimeout(timer); }, [search]);
  useEffect(() => {
    let active = true;
    const params = { target: query, since: from ? new Date(`${from}T00:00:00`).toISOString() : undefined,
      until: to ? new Date(`${to}T23:59:59.999`).toISOString() : undefined, limit: 20, offset: page * 20 };
    api.history(params).then(data => { if (active) { setResult(data); setError(''); } })
      .catch(e => { if (active) { setResult(null); setError(e instanceof Error ? e.message : '历史记录加载失败'); } });
    return () => { active = false; };
  }, [query, from, to, page, revision]);
  function toggle(id: string) {
    setSelected(old => old.includes(id) ? old.filter(key => key !== id)
      : [...old.slice(-1), id]);
  }
  async function remove(record: DiagnosisRecord) {
    if (!window.confirm(`确定删除 ${record.target} 在 ${formatDate(record.created_at)} 的记录吗？此操作无法撤销。`)) return;
    setBusy(true);
    try { await api.removeRecord(record.id); setSelected(s => s.filter(id => id !== record.id));
      setRevision(v => v + 1); onChange(); }
    catch (e) { setError(e instanceof Error ? e.message : '删除失败'); }
    finally { setBusy(false); }
  }
  async function exportAll() {
    try { downloadJson(await api.exportRecords(), 'netcase-records.json'); }
    catch (e) { setError(e instanceof Error ? e.message : '导出失败'); }
  }
  return <div className="interior-page history-page"><div className="interior-heading"><div>
    <div className="eyebrow">A RECORD OF WHAT HAPPENED</div><h1>历史记录</h1>
    <p>查找过去的检测，比较发生变化的地方。</p></div>
    <button className="button secondary" onClick={() => void exportAll()} disabled={!result?.total}><Download size={16} />导出全部</button></div>
    <section className="panel history-panel"><div className="history-filters"><label className="search-input"><Search size={16} />
      <input value={search} onChange={e => setSearch(e.target.value)} placeholder="按域名或地址筛选…" aria-label="按域名或地址筛选历史" /></label>
      <label className="date-input"><CalendarDays size={15} /><span>从</span><input aria-label="起始日期" type="date" value={from} onChange={e => { setFrom(e.target.value); setPage(0); }} /></label>
      <label className="date-input"><CalendarDays size={15} /><span>到</span><input aria-label="结束日期" type="date" value={to} onChange={e => { setTo(e.target.value); setPage(0); }} /></label>
      {(from || to || search) && <button className="text-button" onClick={() => { setSearch(''); setFrom(''); setTo(''); setPage(0); }}>清除筛选</button>}</div>
      <div className="history-title"><div><h2>检测记录</h2><span>{result ? `共 ${result.total} 条` : '加载中…'}</span></div>
        <span>选择两条记录可对比</span></div>
      {error && <div className="history-error" role="alert">{error}<button className="text-button" onClick={() => setRevision(v => v + 1)}>重试</button></div>}
      {result?.items.length ? <div className="table-scroll"><table className="history-table"><thead><tr>
        <th><span className="sr-only">选择比较</span></th><th>检测目标</th><th>诊断状态</th><th>模式 / 来源</th><th>总耗时</th><th>时间</th><th><span className="sr-only">操作</span></th>
      </tr></thead><tbody>{result.items.map(record => <tr key={record.id}><td><input type="checkbox" checked={selected.includes(record.id)} onChange={() => toggle(record.id)} aria-label={`选择比较 ${record.target} ${formatDate(record.created_at)}`} /></td>
        <td><button className="history-target" onClick={() => onOpen(record)}>{record.target}<small>{record.summary}</small></button></td>
        <td><StatusPill status={record.status} /></td><td className="small muted">{modeLabel[record.mode]}<br />{record.source === 'imported' ? '用户导入' : '本机检测'}</td>
        <td className="mono small">{formatDuration(record.duration_ms)}</td><td className="small muted date-cell">{formatDate(record.created_at)}</td>
        <td><div className="row-actions"><button className="icon-button" aria-label={`查看 ${record.target}`} onClick={() => onOpen(record)}><ArrowRight size={16} /></button>
          <button className="icon-button" disabled={busy} aria-label={`删除 ${record.target}`} onClick={() => void remove(record)}><Trash2 size={15} /></button></div></td>
      </tr>)}</tbody></table></div> : !error && <div className="history-empty"><Clock3 size={28} /><h3>{result ? '没有符合条件的记录' : '正在读取历史记录…'}</h3>
        <p>{result ? '调整日期或目标筛选，或者先执行一次诊断。' : '连接本地数据库中。'}</p></div>}
      <div className="history-footer"><span>第 {page + 1} 页{result ? ` · 共 ${Math.max(1, Math.ceil(result.total / 20))} 页` : ''}</span><div>
        <button className="icon-button" aria-label="上一页" disabled={page === 0} onClick={() => setPage(p => p - 1)}><ChevronLeft size={16} /></button>
        <button className="icon-button" aria-label="下一页" disabled={!result || (page + 1) * 20 >= result.total} onClick={() => setPage(p => p + 1)}><ChevronRight size={16} /></button>
      </div></div></section>
    {selected.length > 0 && <div className="comparison-dock"><ArrowLeftRight size={17} /><span>已选择 {selected.length} / 2 条记录</span>
      <button className="button primary" disabled={selected.length !== 2} onClick={() => onCompare(selected[0], selected[1])}>比较差异<ArrowRight size={15} /></button>
      <button className="text-button" onClick={() => setSelected([])}>取消</button></div>}
  </div>;
}
