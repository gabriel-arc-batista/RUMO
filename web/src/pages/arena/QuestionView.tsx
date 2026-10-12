import { Check, CircleSlash, X } from "lucide-react";
import type { ReactNode } from "react";
import type { AttemptState } from "../../domain/projection";
import type { Block, Question } from "../../domain/types";

/** Trechos entre crases viram <code>; o resto continua texto simples. */
export function Inline({ text }: { text: string }): ReactNode {
  const parts = text.split(/(`[^`\n]+`)/g);
  return parts.map((part, i) => (part.length > 2 && part.startsWith("`") && part.endsWith("`") ? <code key={i}>{part.slice(1, -1)}</code> : part));
}

export function Statement({ blocks }: { blocks: Block[] }) {
  return (
    <div className="statement">
      {blocks.map((b, i) => {
        if (b.kind === "code")
          return (
            <pre key={i} className="code-block" tabIndex={0} aria-label={`Código${b.lang ? ` ${b.lang}` : ""}`}>
              <code>{b.text}</code>
            </pre>
          );
        if (b.kind === "formula")
          return (
            <p key={i} className="formula" role="math" aria-label={b.text}>
              {b.text}
            </p>
          );
        if (b.kind === "image")
          return (
            <figure key={i} className="statement-figure">
              <img src={b.src} alt={b.alt} loading="lazy" />
              {b.alt && <figcaption className="xs muted">{b.alt}</figcaption>}
            </figure>
          );
        return (
          <p key={i}>
            <Inline text={b.text} />
          </p>
        );
      })}
    </div>
  );
}

/**
 * Alternativas como grupo de rádio. Antes da confirmação, escolher não envia nada.
 * Depois, "Sua resposta" e "Gabarito" aparecem em texto e ícone (não só cor).
 */
export function Options({
  question,
  selected,
  onSelect,
  attempt,
  locked,
}: {
  question: Question;
  selected: string | null;
  onSelect: (id: string) => void;
  attempt: AttemptState | null;
  locked: boolean;
}) {
  const answerKey = attempt?.result?.answer;
  const name = `q-${question.id}`;
  const letter = (i: number) => String.fromCharCode(65 + i);
  return (
    <fieldset className={`options${question.type === "certo_errado" ? " ce" : ""}`} disabled={locked}>
      <legend className="sr-only">Alternativas</legend>
      {question.options.map((o, i) => {
        const chosen = attempt ? attempt.answer === o.id : selected === o.id;
        const isKey = Boolean(answerKey) && answerKey === o.id;
        const state = attempt?.result ? (isKey ? "key" : chosen ? "wrong" : "") : "";
        return (
          <label key={o.id} className={`option${chosen ? " chosen" : ""}${state ? ` ${state}` : ""}`}>
            <input type="radio" name={name} value={o.id} checked={chosen} onChange={() => onSelect(o.id)} />
            {question.type !== "certo_errado" && (
              <span className="option-letter" aria-hidden="true">
                {letter(i)}
              </span>
            )}
            <span className="grow option-text">
              {question.type !== "certo_errado" && <span className="sr-only">{letter(i)}) </span>}
              <Inline text={o.text} />
            </span>
            {attempt?.result && (chosen || isKey) && (
              <span className="option-flags">
                {chosen && (
                  <span className={`tag ${attempt.result.status === "correct" ? "success" : attempt.result.status === "annulled" ? "" : "error"}`}>
                    {attempt.result.status === "correct" ? <Check size={12} aria-hidden="true" /> : attempt.result.status === "annulled" ? <CircleSlash size={12} aria-hidden="true" /> : <X size={12} aria-hidden="true" />}
                    Sua resposta
                  </span>
                )}
                {isKey && !chosen && (
                  <span className="tag success">
                    <Check size={12} aria-hidden="true" /> Gabarito
                  </span>
                )}
                {isKey && chosen && <span className="sr-only">, que é o gabarito</span>}
              </span>
            )}
          </label>
        );
      })}
    </fieldset>
  );
}
