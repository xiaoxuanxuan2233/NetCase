import { useEffect, useState } from 'react';
import { Database, Download, HardDrive, Info, Moon, Save, ShieldCheck, Sun, Trash2 } from 'lucide-react';
import { api, downloadJson, isPreview } from '../services/api';
import type { ModuleName, Settings } from '../types';

const names: { key: ModuleName; label: string }[] = [
  { key: 'dns', label: 'DNS' }, { key: 'tcp', label: 'TCP' }, { key: 'tls', label: 'TLS' },
  { key: 'http', label: 'HTTP' }, { key: 'ping', label: 'Ping' },
  { key: 'traceroute', label: 'Traceroute' },
];

export function SettingsPage({ platform, onTheme, onCleared }: {
  platform: string; onTheme: (value: Settings['theme']) => void; onCleared: () => void;
}) {
  const [value, setValue] = useState<Settings | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    api.settings().then(v => { if (active) setValue(v); })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : '无法读取设置'); });
    return () => { active = false; };
  }, []);

  function update(partial: Partial<Settings>) { setValue(current => current ? { ...current, ...partial } : current); }
  async function save() {
    if (!value) return;
    setBusy(true); setError('');
    try { const saved = await api.saveSettings(value); setValue(saved); onTheme(saved.theme); setNotice('设置已保存，并会用于下一次诊断'); }
    catch (e) { setError(e instanceof Error ? e.message : '保存失败'); }
    finally { setBusy(false); }
  }
  async function exportAll() {
    try { downloadJson(await api.exportRecords(), 'netcase-records.json'); setNotice('记录已导出，请检查文件内容后再分享'); }
    catch (e) { setError(e instanceof Error ? e.message : '导出失败'); }
  }
  async function clear() {
    if (!window.confirm('确定清空所有诊断历史吗？此操作无法撤销。建议先导出备份。')) return;
    setBusy(true); setError('');
    try { await api.clearRecords(); setNotice('所有诊断历史已清空'); onCleared(); }
    catch (e) { setError(e instanceof Error ? e.message : '清理失败'); }
    finally { setBusy(false); }
  }
  const storage = platform === 'Windows' ? '%LOCALAPPDATA%\\NetCase\\netcase.db'
    : platform === 'Darwin' ? '~/.local/share/netcase/netcase.db（可用 XDG_DATA_HOME 调整）'
      : '~/.local/share/netcase/netcase.db（遵循 XDG_DATA_HOME）';

  return <div className="interior-page settings-page"><div className="interior-heading"><div>
    <div className="eyebrow">MADE FOR YOUR WORKFLOW</div><h1>设置</h1>
    <p>控制界面、默认检测行为与本地数据。</p></div>
    <button className="button primary" disabled={!value || busy} onClick={() => void save()}><Save size={16} />{busy ? '保存中…' : '保存设置'}</button></div>
    {error && <p className="inline-notice error" role="alert">{error}</p>}
    {notice && <p className="inline-notice" role="status">{notice}</p>}
    {!value && !error && <div className="panel settings-loading">正在读取设置…</div>}
    {value && <div className="settings-columns"><div className="settings-main">
      <section className="panel settings-section"><div className="panel-heading"><h2><Sun size={18} />外观</h2></div>
        <div className="settings-body"><p>主题会保存在本地服务中，保存后立即生效。</p>
          <div className="theme-choices">{(['system', 'light', 'dark'] as const).map(theme => <label className={value.theme === theme ? 'chosen' : ''} key={theme}>
            <input type="radio" name="theme" checked={value.theme === theme} onChange={() => update({ theme })} />
            {theme === 'dark' ? <Moon size={18} /> : theme === 'light' ? <Sun size={18} /> : <span className="system-icon">◐</span>}
            <strong>{theme === 'system' ? '跟随系统' : theme === 'dark' ? '深色' : '浅色'}</strong></label>)}</div></div></section>
      <section className="panel settings-section"><div className="panel-heading"><h2><Database size={18} />诊断默认值</h2></div>
        <div className="settings-body"><p>只影响之后创建的诊断，不会改写已有记录。</p>
          <label className="field-label">单步超时时间 <span className="muted">1–10 秒</span>
            <select className="plain-input" value={value.timeout_seconds} onChange={e => update({ timeout_seconds: Number(e.target.value) })}>
              {[1, 2, 3, 5, 8, 10].map(v => <option key={v} value={v}>{v} 秒</option>)}</select></label>
          <label className="field-label">默认模式<select className="plain-input" value={value.default_mode}
            onChange={e => update({ default_mode: e.target.value as Settings['default_mode'] })}>
              <option value="quick">快速检查 · DNS / TCP / TLS</option>
              <option value="full">完整诊断 · 全部适用模块</option>
              <option value="custom">自定义 · 按下方模块</option></select></label>
          <div className="field-label">自定义模式默认模块</div><div className="setting-modules">{names.map(({ key, label }) => <label key={key}>
            <input type="checkbox" checked={value.default_modules.includes(key)}
              onChange={() => { const next = value.default_modules.includes(key)
                ? value.default_modules.filter(v => v !== key) : [...value.default_modules, key];
              if (next.length) update({ default_modules: next }); }} />{label}</label>)}</div>
          <p className="form-hint"><Info size={14} />未选择的依赖模块可能为连接检查自动执行 DNS，以确保结果有依据。</p>
        </div></section>
      <section className="panel settings-section danger-section"><div className="panel-heading"><h2><HardDrive size={18} />本地数据</h2></div>
        <div className="settings-body"><p>检测记录、收藏与草稿只保存在当前设备。不会上传到 NetCase 服务。</p>
          <div className="storage-location"><strong>默认数据库位置</strong><code>{isPreview ? '浏览器 localStorage（仅独立预览）' : storage}</code></div>
          <p>可通过环境变量 <code>NETCASE_DATA_DIR</code> 指定数据目录。主题在浏览器也保存一份，用于页面打开前选择配色。</p>
          <div className="data-actions"><button className="button secondary" disabled={isPreview} onClick={() => void exportAll()}><Download size={16} />导出全部记录（脱敏 JSON）</button>
            <button className="button danger" disabled={isPreview || busy} onClick={() => void clear()}><Trash2 size={16} />清空历史记录</button></div>
          <p className="form-hint"><ShieldCheck size={14} />导出前会过滤 URL 查询串、常见敏感字段与非公网 IP；分享前仍需人工检查。</p>
        </div></section></div>
      <aside className="settings-aside"><div className="aside-tip"><ShieldCheck size={20} /><h3>隐私默认设置</h3>
        <p>后端仅监听 127.0.0.1。无账号、无遥测，不查询第三方 IP 归属。公开 DNS 必须由你手动选择。</p></div>
        <div className="settings-help"><h3>实际影响</h3><p>超时与默认模式会在“新建诊断”预填；主题在保存时更新。历史清理会从 SQLite 删除记录，无法撤销。</p></div></aside>
    </div>}
  </div>;
}
