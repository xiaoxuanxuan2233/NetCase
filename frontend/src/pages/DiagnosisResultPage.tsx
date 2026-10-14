import { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, ChevronDown, Clipboard, Clock3, Download,
  FileJson, Globe2, Info, Lightbulb, ShieldCheck } from 'lucide-react';
import { api } from '../services/api';
import { formatDate, formatDuration, modeLabel } from '../services/format';
import type { DiagnosisRecord } from '../types';
import { StatusPill } from '../components/Primitives';

export function DiagnosisResultPage({ record: initial, onHistory, onBack, onUpdated }: {
  record: DiagnosisRecord; onHistory: () => void; onBack: () => void;
  onUpdated: (record: DiagnosisRecord) => void;
}) {
  const [notes, setNotes] = useState(initial.notes);
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const record = initial;
  const first = record.conclusions?.[0];
  const source = record.source === 'imported';

  async function copy() {
    try {
      await navigator.clipboard.writeText(`${record.target}\n${record.summary}\n${record.modules.map(m => `${m.name.toUpperCase()}: ${m.detail}`).join('\n')}`);
      setMessage('已复制结果摘要');
    } catch { setMessage('浏览器没有授予剪贴板权限，可下载报告。'); }
  }
  async function save() {
    setSaving(true);
    try { onUpdated(await api.saveNote(record.id, notes)); setMessage('备注已保存'); }
    catch (e) { setMessage(e instanceof Error ? e.message : '保存备注失败'); }
    finally { setSaving(false); }
  }
  async function download(format: 'markdown' | 'json' | 'html') {
    try { await api.downloadReport(record.id, format); setMessage('报告已下载，分享前请再次检查敏感内容'); }
    catch (e) { setMessage(e instanceof Error ? e.message : '报告导出失败'); }
  }
  return <div className="interior-page result-page"><div className="interior-heading"><div>
    <button className="text-button muted back-link" onClick={onBack}><ArrowLeft size={15} />返回</button>
    <div className="eyebrow">DIAGNOSIS / {record.id.slice(0, 8)}</div><h1>诊断结果</h1>
    <p>清楚地看见事实，再决定下一步。</p></div>
    <button className="button secondary" onClick={onHistory}>查看历史记录<ArrowRight size={15} /></button></div>
    {source && <div className="import-warning"><Info size={16} />这份记录由用户导入。NetCase 没有重新检测或独立验证内容。</div>}
    <section className={`result-hero panel ${record.status}`}><div className="result-hero-top"><span className="eyebrow">OVERALL RESULT</span><StatusPill status={record.status} /></div>
      <div className="result-hero-title"><span className="result-orb"><Globe2 size={27} /></span><div>
        <h2>{record.summary}</h2><p>{record.target}</p></div></div>
      <div className="result-meta"><span><Clock3 size={14} />{formatDate(record.created_at)}（本地时间）</span>
        <span>{modeLabel[record.mode]}</span><span>整体诊断耗时 {formatDuration(record.duration_ms)}</span>
        <span>规则版本 {record.rule_version}</span></div></section>
    <div className="result-columns"><div className="result-main">
      <section className="panel explanation-panel"><div className="panel-heading"><h2><Lightbulb size={17} />这意味着什么</h2>
        <span className="small muted">基于规则和实际模块证据</span></div>
        {record.conclusions?.length ? <div className="conclusion-list">{record.conclusions.map((item, i) => <article key={i} className={`conclusion ${item.level}`}>
          <div className="conclusion-top"><span className="conclusion-index">{String(i + 1).padStart(2, '0')}</span>
            <h3>{item.title}</h3><span className="confidence">{item.confidence}</span></div>
          <div className="conclusion-detail"><div><strong>检测依据</strong><ul>{item.evidence.map((part, j) => <li key={j}>{part}</li>)}</ul></div>
            {item.possible_causes.length > 0 && <div><strong>可能原因</strong><ul>{item.possible_causes.map((part, j) => <li key={j}>{part}</li>)}</ul></div>}
            <div><strong>下一步建议</strong><ul>{item.next_steps.map((part, j) => <li key={j}>{part}</li>)}</ul></div>
            <p className="knowledge"><Info size={14} />{item.knowledge}</p></div></article>)}</div>
          : <div className="legacy-message">这份导入记录没有结构化分析结论。请查看各模块实际结果。</div>}
      </section>
      <section className="panel modules-result"><div className="panel-heading"><h2>分模块检测</h2><span className="small muted">点击展开原始证据</span></div>
        <div className="module-results">{record.modules.map(module => <details key={module.name} className="module-result">
          <summary><span className={`module-result-symbol ${module.status}`}><Check size={17} /></span>
            <div><strong className="mono">{module.name.toUpperCase()}</strong><small>{module.detail}</small></div>
            <StatusPill status={module.status} /><span className="mono timing">{formatDuration(module.duration_ms)}</span><ChevronDown size={16} /></summary>
          <div className="module-raw"><div><strong>本次检测的证据</strong>{module.error_type && <code>{module.error_type}</code>}</div>
            <pre>{JSON.stringify(module.evidence, null, 2)}</pre></div></details>)}</div>
      </section>
    </div><div className="result-side">
      <section className="panel report-panel"><div className="panel-heading"><h2><Download size={17} />导出报告</h2></div>
        <p>分享给 GitHub Issue 或技术支持。导出时会脱敏 URL 查询串、常见敏感字段和私网 IPv4。</p>
        <div className="report-actions"><button onClick={() => void download('markdown')}><span>MD</span><div><strong>Markdown</strong><small>适合 Issue 与论坛</small></div><ArrowRight size={15} /></button>
          <button onClick={() => void download('json')}><span><FileJson size={18} /></span><div><strong>JSON</strong><small>结构化技术证据</small></div><ArrowRight size={15} /></button>
          <button onClick={() => void download('html')}><span>H</span><div><strong>HTML</strong><small>整洁的独立网页</small></div><ArrowRight size={15} /></button></div>
        <button className="button secondary copy-button" onClick={() => void copy()}><Clipboard size={15} />复制结果摘要</button></section>
      <section className="panel conditions-panel"><div className="panel-heading"><h2>本次检测条件</h2></div>
        <dl><div><dt>网络环境</dt><dd>{record.environment}</dd></div>
          <div><dt>DNS 解析器</dt><dd>{String((record.context?.resolver as { resolver?: string } | undefined)?.resolver ?? '未记录')}</dd></div>
          <div><dt>地址族</dt><dd>{Array.isArray(record.context?.address_families) ? record.context.address_families.join(' / ') : '未记录'}</dd></div>
          <div><dt>端口</dt><dd>{String(record.context?.port ?? '未记录')}</dd></div></dl></section>
      <section className="panel notes-panel"><div className="panel-heading"><h2>我的备注</h2></div><div className="notes-body">
        <textarea value={notes} onChange={e => setNotes(e.target.value)} maxLength={1000}
          placeholder="记录网络环境、复现条件或你观察到的异常…" rows={4} />
        <button className="button secondary" disabled={saving || notes === record.notes} onClick={() => void save()}>
          {saving ? '保存中…' : '保存备注'}</button></div></section>
      <div className="result-limits"><ShieldCheck size={16} /><p>结论只适用于当时的目标和检测条件。不同 DNS、IPv4/IPv6 或网络环境的结果可能不同。</p></div>
      {first && <div className="result-limits"><Info size={16} /><p>置信程度“{first.confidence}”由规则分级，不是生成的百分数。</p></div>}
    </div></div>
    {message && <p className="inline-notice" role="status">{message}</p>}
  </div>;
}
