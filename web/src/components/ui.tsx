import { AlertTriangle, CloudOff, Inbox, RotateCw } from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { portraitLayers, type Look } from "../domain/character";

export function ExampleTag({ title = "Dado de exemplo: não é conteúdo publicado nem revisado." }: { title?: string }) {
  return (
    <span className="tag example" title={title}>
      EXEMPLO
    </span>
  );
}

export function Portrait({ size = 40, look }: { size?: number; look?: Look }) {
  return (
    <span className="portrait" style={{ width: size, height: size }} aria-hidden="true">
      {portraitLayers(look).map((src) => (
        <img key={src} src={src} alt="" loading="lazy" decoding="async" />
      ))}
    </span>
  );
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T;
  onChange: (value: T) => void;
  options: { value: T; label: ReactNode; count?: number }[];
  label: string;
}) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}>
          {o.label}
          {o.count !== undefined && <span className="n">{o.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  children,
  action,
  compact,
}: {
  icon?: ReactNode;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}) {
  return (
    <div className={`state${compact ? " compact" : ""}`}>
      {icon ?? <Inbox size={28} aria-hidden="true" />}
      <h2>{title}</h2>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ title, message, onRetry }: { title: string; message?: string; onRetry?: () => void }) {
  return (
    <div className="state" role="alert">
      <AlertTriangle size={28} aria-hidden="true" />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
      {onRetry && (
        <button className="btn" type="button" onClick={onRetry}>
          <RotateCw size={16} aria-hidden="true" /> Tentar de novo
        </button>
      )}
    </div>
  );
}

export function OfflineState({ what }: { what: string }) {
  return (
    <EmptyState icon={<CloudOff size={28} aria-hidden="true" />} title="Sem conexão">
      {what} precisa de internet para carregar. O que você já marcou fica guardado neste navegador e é enviado quando a conexão voltar.
    </EmptyState>
  );
}

export function Loading({ label = "Carregando…", lines = 3 }: { label?: string; lines?: number }) {
  return (
    <div className="stack" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skeleton" style={{ height: i === 0 ? 28 : 56, width: i === 0 ? "40%" : "100%" }} />
      ))}
    </div>
  );
}

/** Diálogo modal acessível: foco preso, Esc fecha, foco volta ao acionador. */
export function Dialog({
  title,
  onClose,
  children,
  actions,
  wide,
  describedBy,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  actions?: ReactNode;
  wide?: boolean;
  describedBy?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const node = ref.current;
    const focusable = () =>
      node ? [...node.querySelectorAll<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])")].filter((el) => !el.hasAttribute("disabled")) : [];
    (node?.querySelector<HTMLElement>("[data-autofocus]") ?? focusable()[0])?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        close.current();
      }
      if (e.key === "Tab") {
        const items = focusable();
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      previous?.focus?.();
    };
  }, []);
  return (
    <div className="dialog-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={ref}
        className={`dialog${wide ? " wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={describedBy}
      >
        <h2 id={titleId}>{title}</h2>
        {children}
        {actions && <div className="dialog-actions">{actions}</div>}
      </div>
    </div>
  );
}

/** Confirmação de ação destrutiva: texto específico e botão com o nome da ação. */
export function Confirm({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const id = useId();
  return (
    <Dialog
      title={title}
      onClose={onCancel}
      describedBy={id}
      actions={
        <>
          <button className="btn" type="button" onClick={onCancel} data-autofocus>
            Cancelar
          </button>
          <button className="btn danger-solid" type="button" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </>
      }
    >
      <p id={id} className="muted">
        {message}
      </p>
    </Dialog>
  );
}

/** Menu "⋯" com teclado: setas, Esc e clique fora fecham. */
export function Menu({
  label,
  icon,
  items,
}: {
  label: string;
  icon: ReactNode;
  items: { label: string; icon?: ReactNode; onSelect: () => void; danger?: boolean }[];
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const first = ref.current?.querySelector<HTMLButtonElement>(".menu-list button");
    first?.focus();
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);
  const onKey = (e: React.KeyboardEvent) => {
    const buttons = [...(ref.current?.querySelectorAll<HTMLButtonElement>(".menu-list button") ?? [])];
    const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === "Escape") {
      setOpen(false);
      button.current?.focus();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      buttons[(index + 1) % buttons.length]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      buttons[(index - 1 + buttons.length) % buttons.length]?.focus();
    }
  };
  return (
    <div className="menu" ref={ref} onKeyDown={onKey}>
      <button
        ref={button}
        type="button"
        className="icon-btn sm"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        {icon}
      </button>
      {open && (
        <div className="menu-list" role="menu">
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              className={item.danger ? "danger" : undefined}
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ProgressBar({ value, max, label, tone }: { value: number; max: number; label: string; tone?: "info" }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div
      className={`bar${tone ? ` ${tone}` : ""}`}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
    >
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}
