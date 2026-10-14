import type { Mode, Status } from '../types';

export const statusLabel: Record<Status, string> = {
  success: '检查通过', warning: '需要关注', failed: '检测失败', unsupported: '未能检测',
};
export const modeLabel: Record<Mode, string> = { quick: '快速检查', full: '完整诊断', custom: '自定义' };
export function formatDuration(ms: number | null) {
  if (ms === null) return '—';
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}
export function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  });
}
export function localDate(value: Date) {
  const shifted = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
  return shifted.toISOString().slice(0, 10);
}
export function displayHost(target: string) {
  try { return new URL(target.includes('://') ? target : `https://${target}`).host; }
  catch { return target; }
}
export function validateTarget(value: string): string {
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > 2048 || /[\s\\]/u.test(trimmed)
    || [...trimmed].some(character => character.charCodeAt(0) < 32)) {
    throw new Error('请输入有效的域名、IP 或 HTTP(S) URL');
  }
  // Full validation and canonicalization is also performed by the local API.
  const rawIpv6 = /^[a-f\d:]+$/i.test(trimmed) && trimmed.includes('::');
  const url = new URL(trimmed.includes('://') ? trimmed : `https://${rawIpv6 ? `[${trimmed}]` : trimmed}`);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || !url.hostname) {
    throw new Error('仅支持不含账号密码的 HTTP(S) URL、域名或 IP');
  }
  if (url.port && (Number(url.port) < 1 || Number(url.port) > 65535)) throw new Error('端口无效');
  if (!trimmed.includes('://') && (url.pathname !== '/' || url.search || url.hash)) {
    throw new Error('含路径的目标请补充 http:// 或 https://');
  }
  return trimmed;
}
