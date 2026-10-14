import { useState } from 'react';
import { Copy, Download, FileJson, Info } from 'lucide-react';
import type { DiagnosisRecord } from '../types';
import { api } from '../services/api';
import { formatDate, formatDuration, modeLabel } from '../services/format';
import { Dialog, StatusPill } from './Primitives';

export function RecordDetail({ record, demo, onClose }: {
  record: DiagnosisRecord; demo: boolean; onClose: () => void;
}) {
  const [message, setMessage] = useState('');
  async function copy() {
    try { await navigator.clipboard.writeText(JSON.stringify(record, null, 2)); setMessage('已复制记录'); }
    catch { setMessage('浏览器未授权剪贴板，请展开原始证据后手动复制。'); }
  }
  return <Dialog title={record.target} eyebrow={demo ? 'EXAMPLE RECORD · 示例记录' : 'SAVED RECORD · 已保存的记录'} onClose={onClose} wide>
    <div className="detail-meta"><StatusPill status={record.status} /><span>{formatDate(record.created_at)}</span>
      <span>{modeLabel[record.mode]}</span><span>总耗时 {formatDuration(record.duration_ms)}</span></div>
    <p className="detail-summary">{record.summary}</p>
    <div className="info-note"><Info size={17} /><p>{demo ? '这是界面示例，没有对目标发起过检测。'
      : record.source === 'imported' ? '这份记录由用户导入；时间、结果与解释来自原报告，NetCase 未重新执行或独立验证。'
        : '此结果仅描述记录中的目标、时间和检测条件。'}</p></div>
    <dl className="detail-properties"><div><dt>环境与条件</dt><dd>{record.environment}</dd></div>
      <div><dt>规则版本</dt><dd className="mono">{record.rule_version}</dd></div></dl>
    <div className="detail-modules">{record.modules.map(module => <div key={module.name}>
      <div><strong className="mono">{module.name.toUpperCase()}</strong><StatusPill status={module.status} />
        <span className="mono">{formatDuration(module.duration_ms)}</span></div><p>{module.detail || '原记录未提供解释。'}</p>
      {module.error_type && <code>{module.error_type}</code>}
    </div>)}</div>
    {record.notes && <p className="record-note">备注：{record.notes}</p>}
    <details className="raw-evidence"><summary><FileJson size={16} />原始技术证据</summary>
      <pre>{JSON.stringify(record, null, 2)}</pre></details>
    <div className="dialog-actions"><span role="status" className="muted">{message}</span>
      <button className="button secondary" onClick={copy}><Copy size={15} />复制</button>
      {!demo && <button className="button primary" onClick={() => void api.downloadReport(record.id, 'json').catch(e => setMessage(e.message))}>
        <Download size={15} />导出记录</button>}</div>
  </Dialog>;
}
