import type { DashboardData, DiagnosisRecord, ModuleResult, Status } from '../types';
import { localDate } from './format';

export function emptyDashboard(days: number): DashboardData {
  return {
    days, timezone_offset_minutes: -new Date().getTimezoneOffset(),
    stats: { total: 0, passed: 0, eligible: 0, issues: 0, median_duration_ms: null },
    activity: Array.from({ length: days }, (_, i) => {
      const date = new Date(); date.setDate(date.getDate() - days + i + 1);
      return { date: localDate(date), count: 0 };
    }),
    errors: [], latest: null, recent: [], favorites: [], drafts: [],
  };
}

export function exampleDashboard(days: number): DashboardData {
  const data = emptyDashboard(days);
  // Explicit UI fixtures. Never inserted into SQLite, exported, or treated as live results.
  const targets = ['api.example.com', 'docs.example.org', 'example.com', 'cdn.example.net'];
  const records: DiagnosisRecord[] = Array.from({ length: 12 }, (_, i) => {
    const created = new Date(); created.setHours(created.getHours() - 1 - i * 12);
    const status: Status = i === 0 || i === 7 ? 'failed' : i === 4 ? 'warning' : 'success';
    const module = (name: ModuleResult['name'], state: Status, ms: number | null,
      detail: string, error: string | null = null): ModuleResult => ({
        name, status: state, duration_ms: ms, error_type: error, detail,
        evidence: name === 'tls' && state === 'failed'
          ? { verify_code: 10, verify_message: 'certificate has expired', fixture: true }
          : { fixture: true },
      });
    return {
      id: `example-${i}`, target: targets[i % 4], created_at: created.toISOString(),
      mode: i % 3 === 0 ? 'full' : 'quick', status, duration_ms: 280 + i * 83,
      summary: status === 'failed' ? 'DNS 解析与 TCP 连接成功，但 TLS 证书验证未通过。'
        : status === 'warning' ? '网络连接成功，服务器返回 HTTP 503，需要检查网站服务状态。'
        : '本次 DNS、TCP 与 TLS 检查均已通过。',
      rule_version: 'example-only', environment: '示例网络 / IPv4 / 系统 DNS',
      notes: '仅用于展示界面，不代表对该域名的实际检测。', source: 'imported',
      modules: [
        module('dns', 'success', 18 + i, '成功获得 A 记录。'),
        module('tcp', 'success', 43 + i * 2, '目标 443 端口可以建立 TCP 连接。'),
        module('tls', status === 'failed' ? 'failed' : 'success', 72 + i,
          status === 'failed' ? '证书验证器报告证书已过期。' : '证书验证通过，协商 TLS 1.3。',
          status === 'failed' ? 'TLS_CERT_EXPIRED' : null),
        ...(i % 3 === 0 || i === 4 ? [module('http', status === 'failed' ? 'unsupported' : status,
          status === 'failed' ? null : 147 + i, status === 'failed' ? 'TLS 未通过，未继续请求。'
            : status === 'warning' ? 'HTTP 503 Service Unavailable。' : 'HTTP 200 OK。',
          status === 'warning' ? 'HTTP_503' : null)] : []),
      ],
    };
  });
  const dates = new Set(data.activity.map(a => a.date));
  const scoped = records.filter(r => dates.has(localDate(new Date(r.created_at))));
  data.stats.total = scoped.length;
  data.stats.eligible = scoped.length;
  data.stats.passed = scoped.filter(r => r.status === 'success').length;
  data.stats.issues = scoped.filter(r => ['failed', 'warning'].includes(r.status)).length;
  const durations = scoped.map(r => r.duration_ms).sort((a, b) => a - b);
  data.stats.median_duration_ms = durations.length
    ? (durations[Math.floor((durations.length - 1) / 2)] + durations[Math.floor(durations.length / 2)]) / 2 : null;
  data.activity = data.activity.map(a => ({ ...a,
    count: scoped.filter(r => localDate(new Date(r.created_at)) === a.date).length }));
  const errors = new Map<string, number>();
  scoped.forEach(r => new Set(r.modules.flatMap(m => m.error_type ? [m.error_type] : []))
    .forEach(e => errors.set(e, (errors.get(e) ?? 0) + 1)));
  data.errors = [...errors].map(([type, count]) => ({ type, count })).sort((a, b) => b.count - a.count);
  data.latest = scoped[0] ?? null;
  data.recent = scoped.slice(0, 8);
  data.favorites = targets.slice(0, 3).map((target, i) => ({
    id: `example-favorite-${i}`, target, label: ['API 服务', '文档站点', '示例站点'][i],
  }));
  return data;
}
