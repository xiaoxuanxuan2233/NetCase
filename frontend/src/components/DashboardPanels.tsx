import { Activity, ArrowDownToLine, ArrowRight, Bookmark, Check, ChevronRight, Clock3,
  Database, Globe2, Layers3, Link2, LockKeyhole, Plus, Search, Server, ShieldCheck,
  Sparkles, Target, Trash2, TriangleAlert } from 'lucide-react';
import { useState } from 'react';
import type { DashboardData, DiagnosisRecord } from '../types';
import { displayHost, formatDate, formatDuration, modeLabel, statusLabel } from '../services/format';
import { StatusPill } from './Primitives';

export function StatCards({ data }: { data: DashboardData }) {
  const { stats } = data;
  const rate = stats.eligible ? Math.round(stats.passed / stats.eligible * 100) : null;
  return <div className="stat-grid">
    <div className="stat-card"><div className="stat-label">诊断记录<Activity size={17} /></div>
      <div className="stat-value">{stats.total}<span>次</span></div>
      <div className="stat-note"><span className="tiny-dot neutral" />近 {data.days} 天已保存的检测</div></div>
    <div className="stat-card"><div className="stat-label">检查通过率<ShieldCheck size={17} /></div>
      <div className="stat-value">{rate ?? '—'}{rate !== null && <span>%</span>}</div>
      <div className="stat-note"><span className={`tiny-dot ${rate !== null ? 'green' : 'neutral'}`} />
        {stats.eligible ? `${stats.passed} / ${stats.eligible} 次有效检测通过` : '完成检测后生成统计'}</div></div>
    <div className="stat-card"><div className="stat-label">需要关注<TriangleAlert size={17} /></div>
      <div className="stat-value">{stats.issues}<span>次</span></div>
      <div className="stat-note"><span className={`tiny-dot ${stats.issues ? 'orange' : 'neutral'}`} />
        {stats.issues ? '包含警告与失败的诊断' : stats.total ? '所选时间内未记录异常' : '暂无检测依据'}</div></div>
    <div className="stat-card"><div className="stat-label">诊断耗时中位数<Clock3 size={17} /></div>
      <div className="stat-value duration">{stats.median_duration_ms === null ? '—' : formatDuration(stats.median_duration_ms)}</div>
      <div className="stat-note"><span className="tiny-dot neutral" />整个诊断耗时，非网络延迟</div></div>
  </div>;
}

export function LatestPanel({ record, onStart, onDemo, onOpen }: {
  record: DiagnosisRecord | null; onStart: () => void; onDemo: () => void; onOpen: (r: DiagnosisRecord) => void;
}) {
  const flow = [{ name: 'dns', icon: Database }, { name: 'tcp', icon: Link2 },
    { name: 'tls', icon: LockKeyhole }, { name: 'http', icon: Globe2 }];
  return <section className={`panel latest-panel ${record ? '' : 'empty'}`}>
    <div className="panel-heading"><h2><span className="section-dot" />最近一次诊断</h2>
      {record ? <span className="small muted">{formatDate(record.created_at)}</span>
        : <span className="subtle-badge">尚未开始</span>}</div>
    <div className="latest-body">
      {record ? <><div className="latest-target"><div className="target-icon"><Globe2 size={21} /></div>
        <div><h3 className="mono">{displayHost(record.target)}</h3><span className="small muted">{modeLabel[record.mode]}<span className="separator">/</span>{record.environment}</span></div>
        <StatusPill status={record.status} /></div>
        <p className="latest-summary">{record.summary}</p></>
        : <><span className="eyebrow">EVERY CONNECTION TELLS A STORY</span>
          <h3 className="empty-headline">看见连接，<br className="mobile-break" />理解问题。</h3>
          <p className="latest-description">从域名解析到安全连接，逐层定位异常。<br />你的第一份网络诊断，从这里开始。</p></>}
      <div className="connection-flow" aria-label="DNS、TCP、TLS、HTTP 检测层次">
        {flow.map(({ name, icon: Icon }) => {
          const result = record?.modules.find(m => m.name === name);
          return <div key={name} className={`flow-step ${result?.status ?? 'pending'}`}>
            <span className="flow-icon"><Icon size={18} /></span><div><strong>{name.toUpperCase()}</strong>
              <small>{result ? statusLabel[result.status] : record ? '未选择' : '等待检测'}</small></div>
            {result?.status === 'success' && <Check className="flow-check" size={12} />}
          </div>;
        })}
      </div>
    </div>
    <div className="latest-footer">{record ? <><span><span className="tiny-dot neutral" />结论仅适用于本次检测</span>
      <button className="text-button" onClick={() => onOpen(record)}>查看检测依据<ArrowRight size={15} /></button></>
      : <><button className="button primary" onClick={onStart}><Plus size={16} />准备首次诊断</button>
        <button className="text-button muted" onClick={onDemo}>先看看示例<ArrowRight size={15} /></button></>}
    </div>
  </section>;
}

export function ActivityPanel({ data }: { data: DashboardData }) {
  return <section className="panel activity-panel"><div className="panel-heading"><h2>诊断活动</h2>
    <span className="small muted">近 {data.days} 天</span></div>
    <div className="activity-total"><strong>{data.stats.total}</strong><span>次诊断</span>
      <span className="chart-legend"><i />已保存</span></div>
    <div className="activity-chart" role="img" aria-label={`近 ${data.days} 天共 ${data.stats.total} 次诊断`}>
      <div className="activity-bars">{data.activity.map((day, index) => <div className="activity-day"
        title={`${day.date}：${day.count} 次诊断`} key={day.date}>
        <div className="activity-bar" style={{ height: `${Math.max(0, day.count / Math.max(1, ...data.activity.map(d => d.count)) * 72)}px` }} />
        <small>{data.days <= 7 || index % 5 === 0 ? day.date.slice(5).replace('-', '/') : ''}</small>
      </div>)}</div>
      {!data.stats.total && <span className="chart-empty">检测记录将在这里形成时间线</span>}
    </div>
  </section>;
}

export function RecentPanel({ data, onOpen, onImport, onExport, canTransfer }: {
  data: DashboardData; onOpen: (r: DiagnosisRecord) => void; onImport: () => void;
  onExport: () => void; canTransfer: boolean;
}) {
  const [filter, setFilter] = useState('');
  const recent = data.recent.filter(r => r.target.toLowerCase().includes(filter.toLowerCase()));
  return <section className="panel recent-panel"><div className="panel-heading"><h2>最近诊断记录
    <span className="count-badge">{data.recent.length}</span></h2><div className="inline-actions">
      <button className="text-button muted" onClick={onImport} disabled={!canTransfer}
        title={canTransfer ? '导入符合 NetCase 格式的报告' : '本地服务连接后可导入真实报告'}><Plus size={14} />导入</button>
      <button className="icon-button" onClick={onExport} disabled={!canTransfer || !data.stats.total}
        aria-label="导出全部诊断记录" title="导出全部已保存记录"><ArrowDownToLine size={16} /></button>
    </div></div>
    <div className="table-toolbar"><label className="search-input"><Search size={15} /><input
      placeholder="筛选最近记录中的目标…" aria-label="筛选最近记录" value={filter} onChange={e => setFilter(e.target.value)} /></label>
      <span className="small muted">最新 8 条</span></div>
    <div className="table-scroll"><table><thead><tr><th>检测目标</th><th>状态</th><th>总耗时</th><th>检测时间</th><th><span className="sr-only">详情</span></th></tr></thead>
      <tbody>{recent.map(record => <tr key={record.id}><td><button className="record-link" onClick={() => onOpen(record)}>
        <span className="domain-glyph">{displayHost(record.target)[0].toUpperCase()}</span><span><strong>{displayHost(record.target)}</strong>
          <small>{modeLabel[record.mode]}</small></span></button></td>
        <td><StatusPill status={record.status} /></td><td className="mono small">{formatDuration(record.duration_ms)}</td>
        <td className="muted small date-cell">{formatDate(record.created_at)}</td>
        <td><button className="icon-button" aria-label={`查看 ${record.target} 的记录`} onClick={() => onOpen(record)}><ChevronRight size={15} /></button></td>
      </tr>)}</tbody></table></div>
    {!recent.length && <div className="table-empty"><span className="empty-icon"><Layers3 size={24} /></span>
      <h3>{filter ? '没有匹配的最近记录' : '每一次诊断，都值得留存'}</h3>
      <p>{filter ? '试试其他目标，或清空筛选条件。' : '检测完成后，你可以在这里回看结果、追踪变化。'}</p>
      {!filter && <span className="small muted">当前时间范围内暂无记录</span>}
    </div>}
    <div className="panel-footnote"><Database size={13} />记录仅保存在当前数据源中。不同检测条件下的结果应谨慎比较。</div>
  </section>;
}

export function FavoritesPanel({ data, onAdd, onStart, onRemove, readOnly }: {
  data: DashboardData; onAdd: () => void; onStart: (target: string) => void;
  onRemove: (id: string) => void; readOnly: boolean;
}) {
  return <section className="panel favorites-panel"><div className="panel-heading"><h2>常用目标
    <span className="count-badge">{data.favorites.length}</span></h2>
    <button className="icon-button" onClick={onAdd} aria-label="添加常用目标" disabled={readOnly}><Plus size={17} /></button></div>
    {data.favorites.length ? <div className="favorite-list">{data.favorites.map(item => <div className="favorite-row" key={item.id}>
      <span className="favorite-icon"><Globe2 size={17} /></span><button className="favorite-target" disabled={readOnly} onClick={() => onStart(item.target)}>
        <strong>{item.label || displayHost(item.target)}</strong><small className="mono">{item.target}</small></button>
      <button className="icon-button remove-favorite" onClick={() => onRemove(item.id)} disabled={readOnly}
        title="取消收藏" aria-label={`取消收藏 ${item.target}`}><Trash2 size={14} /></button>
    </div>)}</div> : <div className="compact-empty"><Bookmark size={23} /><h3>关注你常用的连接</h3><p>收藏网站、API 或内网服务，<br />下次排查，一步直达。</p></div>}
    <button className="add-target" onClick={onAdd} disabled={readOnly}><Plus size={15} />添加目标</button>
  </section>;
}

export function ErrorsPanel({ data }: { data: DashboardData }) {
  const highest = Math.max(1, ...data.errors.map(e => e.count));
  const names: Record<string, string> = { TLS_CERT_EXPIRED: 'TLS 证书过期', HTTP_503: 'HTTP 503 服务不可用',
    DNS_TIMEOUT: 'DNS 查询超时', TCP_TIMEOUT: 'TCP 连接超时' };
  return <section className="panel errors-panel"><div className="panel-heading"><h2>主要错误类型</h2>
    <TriangleAlert size={16} className="muted" /></div>
    {data.errors.length ? <div className="error-list">{data.errors.map((error, i) => <div key={error.type}>
      <div className="error-label"><span title={error.type}>{names[error.type] ?? error.type}</span><strong>{error.count}<small> 次</small></strong></div>
      <div className="error-track"><span style={{ width: `${error.count / highest * 100}%`, opacity: 1 - i * 0.13 }} /></div>
    </div>)}</div> : <div className="compact-empty errors-empty"><ShieldCheck size={25} /><h3>{data.stats.total ? '未记录异常类型' : '暂无异常数据'}</h3>
      <p>{data.stats.total ? '仅说明已保存记录中没有对应错误。' : '开始检测后，这里会汇总需要关注的问题。'}</p></div>}
    <p className="small muted error-disclaimer">按涉及该错误的诊断次数统计，不推断故障归属。</p>
  </section>;
}

export function KnowledgeStrip({ onLearn }: { onLearn: () => void }) {
  return <div className="knowledge-strip"><span className="knowledge-icon"><Sparkles size={18} /></span>
    <p><strong>先理解，再判断。</strong><span>不同 DNS 返回不同 IP，可能只是 CDN 调度，并不一定是 DNS 污染。</span></p>
    <button className="text-button" onClick={onLearn}>了解诊断原则<ArrowRight size={15} /></button></div>;
}

export function EngineNote() {
  return <div className="engine-note"><Server size={15} /><span>NetCase v0.1</span><span className="separator">/</span>
    <span>单目标本机诊断</span><Target size={14} /></div>;
}
