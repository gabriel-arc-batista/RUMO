import { useEffect, useState } from "react";

/**
 * Fórmula LaTeX renderizada pelo KaTeX (carregado só quando há fórmula).
 * Saída HTML + MathML para leitores de tela; nada é executado (trust:false).
 * Se o texto não for LaTeX válido, mostra o texto original em fonte matemática.
 */
export function Formula({ text }: { text: string }) {
  const [html, setHtml] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    void Promise.all([import("katex"), import("katex/dist/katex.min.css")]).then(([mod]) => {
      if (!alive) return;
      try {
        setHtml(
          mod.default.renderToString(text, {
            displayMode: true,
            throwOnError: true,
            strict: "ignore",
            trust: false,
            output: "htmlAndMathml",
            maxSize: 20,
            maxExpand: 200,
          }),
        );
      } catch {
        setHtml(null);
      }
    });
    return () => {
      alive = false;
    };
  }, [text]);
  if (html) return <div className="formula katex-host" dangerouslySetInnerHTML={{ __html: html }} />;
  return (
    <p className="formula" role="math" aria-label={text}>
      {text}
    </p>
  );
}
