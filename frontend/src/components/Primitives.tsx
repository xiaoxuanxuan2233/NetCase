import { useEffect, useRef, type ReactNode } from 'react';
import { Check, CircleHelp, TriangleAlert, X, XCircle } from 'lucide-react';
import type { Status } from '../types';
import { statusLabel } from '../services/format';

export function Logo() {
  return <div className="brand"><span className="brand-mark" aria-hidden="true">
    <svg viewBox="0 0 40 40"><path d="M10 27V13l20 14V13M10 20h20" /></svg>
  </span><span>netcase<span className="brand-dot">.</span></span></div>;
}
export function StatusPill({ status }: { status: Status }) {
  const Icon = status === 'success' ? Check : status === 'warning' ? TriangleAlert
    : status === 'failed' ? XCircle : CircleHelp;
  return <span className={`status-pill ${status}`}><Icon size={12} />{statusLabel[status]}</span>;
}
export function Dialog({ title, eyebrow, onClose, children, wide = false }: {
  title: string; eyebrow?: string; onClose: () => void; children: ReactNode; wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    dialog?.showModal();
    document.body.classList.add('modal-open');
    return () => { dialog?.close(); document.body.classList.remove('modal-open'); previous?.focus(); };
  }, []);
  return <dialog ref={ref} className={`dialog ${wide ? 'wide' : ''}`} onCancel={onClose}
    aria-labelledby="dialog-title" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
    <div className="dialog-inner">
      <div className="dialog-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h2 id="dialog-title">{title}</h2></div>
        <button className="icon-button" onClick={onClose} aria-label="关闭窗口"><X size={20} /></button>
      </div>{children}
    </div>
  </dialog>;
}
