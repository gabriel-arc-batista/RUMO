import { Check, Clock, AlertTriangle } from "lucide-react";
import { memo, useEffect, useRef, useState } from "react";
import { pdfjs, type PDFDocumentProxy } from "./pdf";

export type MarkStatus = "salvo" | "guardando" | "pendente" | "offline" | "conflito" | null;

const fold = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

/**
 * Uma página do PDF: canvas + camada de texto (seleção e busca), renderizada
 * só perto da área visível e liberada ao se afastar (pouca memória).
 * Logo abaixo, a caixa "Li esta página" com o número dela.
 */
export const PageView = memo(function PageView({
  doc,
  page,
  scale,
  size,
  read,
  status,
  disabled,
  highlight,
  onToggle,
  registerRef,
}: {
  doc: PDFDocumentProxy;
  page: number;
  scale: number;
  size: { w: number; h: number };
  read: boolean;
  status: MarkStatus;
  disabled: boolean;
  highlight: string;
  onToggle: (page: number, read: boolean) => void;
  registerRef: (page: number, el: HTMLElement | null) => void;
}) {
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const textLayer = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(false);
  const [failed, setFailed] = useState(false);
  const width = Math.floor(size.w * scale);
  const height = Math.floor(size.h * scale);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const io = new IntersectionObserver(([entry]) => setNear(entry.isIntersecting), { rootMargin: "900px 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    const c = canvas.current;
    const layer = textLayer.current;
    if (!c || !layer) return;
    if (!near) {
      // Libera a memória do bitmap quando a página se afasta.
      c.width = 0;
      c.height = 0;
      layer.replaceChildren();
      return;
    }
    let cancelled = false;
    let task: ReturnType<Awaited<ReturnType<PDFDocumentProxy["getPage"]>>["render"]> | null = null;
    let text: InstanceType<typeof pdfjs.TextLayer> | null = null;
    void (async () => {
      try {
        const pdfPage = await doc.getPage(page);
        if (cancelled) return;
        const viewport = pdfPage.getViewport({ scale });
        const ratio = Math.min(window.devicePixelRatio || 1, 2);
        c.width = Math.floor(viewport.width * ratio);
        c.height = Math.floor(viewport.height * ratio);
        task = pdfPage.render({
          canvas: c,
          canvasContext: c.getContext("2d")!,
          viewport,
          transform: ratio !== 1 ? [ratio, 0, 0, ratio, 0, 0] : undefined,
        });
        await task.promise;
        if (cancelled) return;
        layer.replaceChildren();
        text = new pdfjs.TextLayer({ textContentSource: pdfPage.streamTextContent(), container: layer, viewport });
        await text.render();
        setFailed(false);
      } catch (error) {
        if (!cancelled && (error as { name?: string })?.name !== "RenderingCancelledException") setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      task?.cancel();
      text?.cancel();
    };
  }, [doc, page, scale, near]);

  // Destaque da busca: marca os trechos da camada de texto que contêm o termo.
  useEffect(() => {
    const layer = textLayer.current;
    if (!layer) return;
    const needle = fold(highlight.trim());
    layer.querySelectorAll("span").forEach((span) => {
      span.classList.toggle("hit", needle.length >= 2 && fold(span.textContent ?? "").includes(needle));
    });
  });

  const id = `li-pagina-${page}`;
  return (
    <section className="pdf-page" aria-label={`Página ${page}`} ref={(el) => registerRef(page, el)} data-page={page}>
      <div ref={wrap} className="pdf-sheet" style={{ width, height, ["--total-scale-factor" as string]: scale }}>
        <canvas ref={canvas} style={{ width, height }} aria-hidden="true" />
        <div ref={textLayer} className="textLayer" />
        {failed && (
          <div className="pdf-failed" role="alert">
            Não foi possível desenhar esta página.
          </div>
        )}
      </div>
      <div className="page-mark" style={{ width: Math.max(width, 260) }}>
        <label className={`check mark-box${read ? " is-read" : ""}`} htmlFor={id}>
          <input id={id} type="checkbox" checked={read} disabled={disabled} onChange={(e) => onToggle(page, e.target.checked)} />
          <span>
            Li esta página <span className="tabular faint">({page})</span>
          </span>
        </label>
        <MarkBadge status={status} />
      </div>
    </section>
  );
});

export function MarkBadge({ status }: { status: MarkStatus }) {
  if (!status) return null;
  if (status === "salvo")
    return (
      <span className="mark-status" title="Salvo na sua conta">
        <Check size={14} aria-hidden="true" /> salvo
      </span>
    );
  if (status === "conflito")
    return (
      <span className="mark-status error">
        <AlertTriangle size={14} aria-hidden="true" /> conflito
      </span>
    );
  return (
    <span className="mark-status warn">
      <Clock size={14} aria-hidden="true" /> {status === "guardando" ? "guardando…" : status === "offline" ? "guardado; envia ao reconectar" : "enviando…"}
    </span>
  );
}
