import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { DashboardData, Health } from '../types';

export function useDashboard(days: number, revision: number) {
  const [state, setState] = useState<{
    data: DashboardData | null; health: Health | null; error: string | null; loading: boolean;
  }>({ data: null, health: null, error: null, loading: true });
  useEffect(() => {
    const abort = new AbortController();
    queueMicrotask(() => {
      if (!abort.signal.aborted) setState(s => ({ ...s, error: null, loading: true }));
    });
    Promise.all([api.dashboard(days, abort.signal), api.health(abort.signal)])
      .then(([data, health]) => { if (!abort.signal.aborted) setState({ data, health, error: null, loading: false }); })
      .catch(error => { if (!abort.signal.aborted) setState({ data: null, health: null,
        error: error instanceof Error ? error.message : '无法读取本地数据', loading: false }); });
    return () => abort.abort();
  }, [days, revision]);
  return state;
}
