import { useState } from "react";
import { Dialog } from "../../components/ui";

/** Correspondência explícita entre versões: a pessoa confere as páginas antes de marcar. */
export function CarryDialog({
  source,
  target,
  initial,
  limit,
  parse,
  onCancel,
  onConfirm,
}: {
  source: string;
  target: string;
  initial: string;
  limit: number;
  parse: (text: string, limit: number) => number[];
  onCancel: () => void;
  onConfirm: (pages: number[]) => void;
}) {
  const [value, setValue] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  return (
    <Dialog
      title="Trazer marcações da versão anterior"
      onClose={onCancel}
      actions={
        <>
          <button className="btn" type="button" onClick={onCancel}>
            Cancelar
          </button>
          <button
            className="btn primary"
            type="button"
            onClick={() => {
              try {
                onConfirm(parse(value, limit));
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Marcar estas páginas
          </button>
        </>
      }
    >
      <p className="muted">
        Páginas lidas na versão {source}. As páginas da versão {target} podem ter mudado: mantenha só as que correspondem ao mesmo conteúdo.
        A versão {source} continua com as marcações dela.
      </p>
      <div className="field">
        <label htmlFor="carry-pages">Páginas a marcar nesta versão</label>
        <input
          id="carry-pages"
          className="input"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setError(null);
          }}
          aria-invalid={Boolean(error)}
          aria-describedby="carry-hint"
          data-autofocus
        />
        <span className="hint" id="carry-hint">
          Ex.: 1-8, 10, 12-14 (1 a {limit})
        </span>
        {error && (
          <span className="error-text" role="alert">
            {error}
          </span>
        )}
      </div>
    </Dialog>
  );
}
