import { useState, type FormEvent } from 'react';
import { ArrowRight, BookmarkPlus, Info, Save } from 'lucide-react';
import { api } from '../services/api';
import { validateTarget } from '../services/format';
import { Dialog } from './Primitives';

export function TargetForm({ kind, initial, onClose, onSaved }: {
  kind: 'favorite' | 'draft'; initial: string; onClose: () => void; onSaved: () => void;
}) {
  const [target, setTarget] = useState(initial);
  const [label, setLabel] = useState('');
  const [port, setPort] = useState('');
  const [mode, setMode] = useState<'quick' | 'full'>('quick');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const favorite = kind === 'favorite';
  async function submit(e: FormEvent) {
    e.preventDefault(); setError('');
    try {
      const valid = validateTarget(target);
      const number = port ? Number(port) : null;
      if (number !== null && (!Number.isInteger(number) || number < 1 || number > 65535)) {
        throw new Error('请输入 1–65535 之间的单个端口');
      }
      setBusy(true);
      if (favorite) await api.favorite(valid, label.trim());
      else await api.draft({ target: valid, port: number, mode });
      onSaved();
    } catch (e) { setError(e instanceof Error ? e.message : '保存失败，请重试'); }
    finally { setBusy(false); }
  }
  return <Dialog title={favorite ? '添加常用目标' : '准备一次诊断'}
    eyebrow={favorite ? 'SAVED TARGET' : 'NEW DIAGNOSIS'} onClose={onClose}>
    <p className="dialog-description">{favorite ? '把常用的网站或服务留在手边。收藏不会发起网络请求。'
      : '先保存目标与检测方式，方便下一阶段接入诊断引擎。'}</p>
    <form onSubmit={submit} className="target-form">
      <label>域名、IP 或 URL<input autoFocus value={target} onChange={e => setTarget(e.target.value)}
        placeholder="例如 example.com 或 https://example.com" required maxLength={2048}
        autoComplete="off" spellCheck={false} /></label>
      {favorite ? <label>显示名称 <span className="muted">可选</span><input value={label}
        onChange={e => setLabel(e.target.value)} placeholder="例如：我的个人网站" maxLength={60} /></label>
        : <>
          <label>TCP 端口 <span className="muted">可选</span><input type="number" value={port}
            onChange={e => setPort(e.target.value)} min={1} max={65535} step={1} placeholder="按 URL 协议自动选择" /></label>
          <fieldset><legend>检测模式</legend><div className="mode-options">
            <label className={mode === 'quick' ? 'selected' : ''}><input type="radio" name="mode"
              checked={mode === 'quick'} onChange={() => setMode('quick')} /><span><strong>快速检查</strong><small>DNS · TCP · TLS</small></span></label>
            <label className={mode === 'full' ? 'selected' : ''}><input type="radio" name="mode"
              checked={mode === 'full'} onChange={() => setMode('full')} /><span><strong>完整诊断</strong><small>全部适用模块</small></span></label>
          </div></fieldset>
          <div className="info-note"><Info size={17} /><p>当前版本完成 Dashboard。诊断引擎尚未接入，保存后不会执行检测，也不会生成检测结果。</p></div>
        </>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="dialog-actions"><button className="button secondary" type="button" onClick={onClose}>取消</button>
        <button className="button primary" disabled={busy} type="submit">
          {favorite ? <BookmarkPlus size={16} /> : <Save size={16} />}
          {busy ? '正在保存…' : favorite ? '保存目标' : '保存检测草稿'}<ArrowRight size={15} />
        </button></div>
    </form>
  </Dialog>;
}
