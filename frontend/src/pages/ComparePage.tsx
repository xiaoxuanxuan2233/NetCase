import { useEffect, useState } from 'react';
import { ArrowLeft, ArrowLeftRight, Clock3, Info } from 'lucide-react';
import { api } from '../services/api';
import { formatDate, formatDuration } from '../services/format';
import type { Comparison } from '../types';
import { StatusPill } from '../components/Primitives';

const conditionNames: Record<string, string> = { target: '目标', network_label: '网络标记',
  resolver: 'DNS 解析器', address_families: '地址族', port: '端口', modules: '检测项目', time: '检测时间' };

export function ComparePage({ left, right, onBack }: { left: string; right: string; onBack: () => void }) {
  const [data, setData] = useState<Comparison | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api.compare(left, right).then(v => { if (active) setData(v); })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : '比较失败'); });
    return () => { active = false; };
  }, [left, right]);
  const differences = data && Object.entries(data.conditions_equal).filter(entry => !entry[1]);
  return <div className="interior-page compare-page"><div className="interior-heading"><div>
    <button className="text-button muted back-link" onClick={onBack}><ArrowLeft size={15} />历史记录</button>
    <div className="eyebrow">CONTEXT CHANGES EVERYTHING</div><h1>诊断对比</h1>
    <p>比较两次检测的结果，同时保留条件差异。</p></div><ArrowLeftRight size={29} className="muted" /></div>
    {error && <div className="history-error" role="alert">{error}</div>}
    {!data && !error && <section className="panel history-empty">正在读取两次诊断记录…</section>}
    {data && <><div className="compare-intro"><Info size={17} /><span>{data.caution}</span></div>
      <div className="compare-headings">{([data.left, data.right] as const).map((record, i) => <section key={record.id} className="panel">
        <span className="eyebrow">{i ? 'AFTER / 第二次' : 'BEFORE / 第一次'}</span>
        <h2>{record.target}</h2><StatusPill status={record.status} />
        <p>{record.summary}</p><p className="small muted">环境：{record.environment}</p>
        <div><Clock3 size={14} />{formatDate(record.created_at)} · {formatDuration(record.duration_ms)}</div>
      </section>)}</div>
      <section className="panel condition-panel"><div className="panel-heading"><h2>检测条件</h2>
        <span className="small muted">不同条件会影响结果解释</span></div>
        <div className="condition-tags">{Object.entries(data.conditions_equal).map(([key, equal]) => <span key={key} className={equal ? 'same' : 'different'}>
          {conditionNames[key] ?? key}<strong>{equal ? '相同' : '不同'}</strong></span>)}</div>
        {differences && differences.length > 0 && <p className="comparison-caution">{differences.map(([key]) => conditionNames[key] ?? key).join('、')}不同。请谨慎解释耗时与状态变化。</p>}</section>
      <section className="panel comparison-results"><div className="panel-heading"><h2>共同检测模块的变化</h2></div>
        {data.changes.length ? data.changes.map(row => <div className="compare-row" key={row.module}>
          <strong className="mono">{row.module.toUpperCase()}</strong><div><StatusPill status={row.before.status} /><p>{row.before.detail}</p></div>
          <ArrowLeftRight size={15} className="muted" /><div><StatusPill status={row.after.status} /><p>{row.after.detail}</p></div>
          <span className="mono compare-delta">{row.duration_delta_ms === null ? '—' : `${row.duration_delta_ms > 0 ? '+' : ''}${row.duration_delta_ms} ms`}</span>
        </div>) : <p className="legacy-message">两次诊断没有共同检测的模块。</p>}
      </section></>}
  </div>;
}
