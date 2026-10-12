import { ArrowLeft, Bookmark, ChevronLeft, ChevronRight, ListTree, Maximize2, Minus, NotebookPen, Plus, Search, SunDim, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { StudyTimer, useStudyTimer } from "../../components/StudyTimer";
import { EmptyState, ErrorState, ExampleTag, Loading, OfflineState, ProgressBar } from "../../components/ui";
import { isComplete, readingKey, type NoteState } from "../../domain/projection";
import type { Lesson, OutlineItem } from "../../domain/types";
import { uuid } from "../../lib/ids";
import { pageRanges, parseRanges } from "../../lib/ranges";
import { CarryDialog } from "./CarryDialog";
import { entity } from "../../service/contract";
import { useCatalog, useRumo } from "../../service/store";
import { CardEditor, type CardDraft } from "../cards/CardEditor";
import { lessonPath, topicName } from "./lessons";
import { MarkBadge, PageView, type MarkStatus } from "./PageView";
import { openPdf, readOutline, type PDFDocumentProxy } from "./pdf";
import { BookmarksPanel, NotesPanel, OutlinePanel, SearchPanel, type PanelTab } from "./ReaderPanel";

type Zoom = { mode: "largura" | "pagina" | "livre"; scale: number };

export default function Reader() {
  const { lessonId = "" } = useParams();
  const catalog = useCatalog();
  const lesson = catalog.lessons.find((l) => l.id === lessonId);
  if (!lesson) {
    return (
      <div className="page">
        <EmptyState title="Aula indisponível" action={<Link className="btn" to="/campo">Voltar ao Campo</Link>}>
          Esta aula não está no catálogo atual.
        </EmptyState>
      </div>
    );
  }
  if (lesson.status !== "disponivel" || !lesson.pdfUrl) {
    return (
      <div className="page">
        <EmptyState title="PDF ainda não publicado" action={<Link className="btn" to={lessonPath(lesson)}>Ver detalhes da aula</Link>}>
          Esta aula está planejada. O leitor abre quando a versão revisada do PDF for publicada.
        </EmptyState>
      </div>
    );
  }
  return <ReaderView key={`${lesson.id}@${lesson.version}`} lesson={lesson} />;
}

function ReaderView({ lesson }: { lesson: Lesson }) {
  const catalog = useCatalog();
  const { sync, enqueue, prefs, setPrefs, toast, online } = useRumo();
  const [params, setParams] = useSearchParams();
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [sizes, setSizes] = useState<{ w: number; h: number }[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pdfOutline, setPdfOutline] = useState<OutlineItem[]>([]);
  const [zoom, setZoom] = useState<Zoom>({ mode: "largura", scale: 1 });
  const [box, setBox] = useState({ w: 800, h: 600 });
  const [current, setCurrent] = useState(Number(params.get("pagina")) || 1);
  const [pageInput, setPageInput] = useState(String(current));
  const [query, setQuery] = useState("");
  const [savingMarks, setSavingMarks] = useState(new Map<number, { read: boolean; token: number }>());
  const markToken = useRef(0);
  const [cardDraft, setCardDraft] = useState<CardDraft | null>(null);
  const [resumeOffer, setResumeOffer] = useState<number | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const pageEls = useRef(new Map<number, HTMLElement>());
  const ratios = useRef(new Map<number, number>());
  const interacted = useRef(false);
  const initialJump = useRef(Number(params.get("pagina")) || 0);
  const lastPositionSent = useRef<number | null>(null);
  const completedBefore = useRef<boolean | null>(null);
  const timer = useStudyTimer(`aula.${lesson.id}.${lesson.version}`);

  const panel = (params.get("painel") as PanelTab | null) ?? null;
  const setPanel = (tab: PanelTab | null) => {
    const next = new URLSearchParams(params);
    if (tab) next.set("painel", tab);
    else next.delete("painel");
    next.delete("pagina");
    setParams(next, { replace: true });
  };

  const pages = lesson.pages ?? doc?.numPages ?? 0;
  const p = sync?.projection;
  const reading = p?.reading.get(readingKey(lesson.id, lesson.version));
  const readSet = useMemo(() => {
    const selected = new Set([...(reading?.marks.entries() ?? [])].filter(([, m]) => m.read).map(([n]) => n));
    savingMarks.forEach((mark, page) => { if (mark.read) selected.add(page); else selected.delete(page); });
    return selected;
  }, [reading, savingMarks]);
  const complete = isComplete(reading, lesson.pages);
  // Outra versão desta aula com páginas lidas: nada é herdado sem confirmação.
  const older = useMemo(() => {
    if (!p || readSet.size) return null;
    let best: { version: string; pages: number[] } | null = null;
    for (const state of p.reading.values()) {
      if (state.lessonId !== lesson.id || state.version === lesson.version) continue;
      const read = [...state.marks.entries()].filter(([, m]) => m.read).map(([n]) => n);
      if (read.length && (!best || read.length > best.pages.length)) best = { version: state.version, pages: read };
    }
    return best;
  }, [p, lesson, readSet.size]);
  const [carry, setCarry] = useState<null | { version: string; pages: number[] }>(null);
  const [carryHidden, setCarryHidden] = useState(false);
  const mismatch = Boolean(doc && lesson.pages && doc.numPages !== lesson.pages);

  // Carrega o PDF e as dimensões de cada página (para reservar o espaço certo).
  useEffect(() => {
    let alive = true;
    const task = openPdf(lesson.pdfUrl!);
    task.promise
      .then(async (d) => {
        const dims: { w: number; h: number }[] = [];
        for (let i = 1; i <= d.numPages; i += 1) {
          const vp = (await d.getPage(i)).getViewport({ scale: 1 });
          dims.push({ w: vp.width, h: vp.height });
        }
        if (!alive) return;
        setSizes(dims);
        setDoc(d);
        setPdfOutline(await readOutline(d));
      })
      .catch((e: unknown) => alive && setLoadError(e instanceof Error ? e.message : "Falha ao abrir o PDF."));
    return () => {
      alive = false;
      void task.destroy();
    };
  }, [lesson.pdfUrl]);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setBox({ w: entry.contentRect.width, h: entry.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, [doc]);

  const maxW = sizes.length ? Math.max(...sizes.map((s) => s.w)) : 595;
  const maxH = sizes.length ? Math.max(...sizes.map((s) => s.h)) : 842;
  // "Largura" ocupa o leitor, mas sem passar de ~920 px: linhas longas cansam.
  const fitWidth = Math.max(0.4, Math.min(box.w - 32, 920) / maxW);
  const scale =
    zoom.mode === "largura"
      ? Math.min(fitWidth, 2.4)
      : zoom.mode === "pagina"
        ? Math.max(0.4, Math.min((box.w - 32) / maxW, (box.h - 72) / maxH))
        : zoom.scale;
  const rounded = Math.round(scale * 100) / 100;

  // Página atual = a mais visível no leitor.
  useEffect(() => {
    const root = scroller.current;
    if (!root || !doc) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) ratios.current.set(Number((e.target as HTMLElement).dataset.page), e.intersectionRatio);
        let best = 0;
        let bestRatio = 0;
        ratios.current.forEach((r, page) => {
          if (r > bestRatio + 0.01 || (Math.abs(r - bestRatio) <= 0.01 && page < best)) {
            best = page;
            bestRatio = r;
          }
        });
        if (best) setCurrent(best);
      },
      { root, threshold: [0, 0.15, 0.3, 0.5, 0.7, 0.9, 1] },
    );
    pageEls.current.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [doc, rounded]);

  useEffect(() => setPageInput(String(current)), [current]);

  const goTo = useCallback(
    (page: number, user = true) => {
      const target = Math.min(Math.max(1, page), pages || 1);
      if (user) interacted.current = true;
      const el = pageEls.current.get(target);
      const root = scroller.current;
      // Rola só o leitor (scrollIntoView rolaria a janela e esconderia o cabeçalho).
      if (el && root) {
        const top = root.scrollTop + el.getBoundingClientRect().top - root.getBoundingClientRect().top - 16;
        root.scrollTo({ top, behavior: prefs.motion === "reduce" || !user ? "auto" : "smooth" });
      }
      setCurrent(target);
    },
    [pages, prefs.motion],
  );

  // Abertura: vai à página pedida; sem pedido, oferece retomar a última posição.
  useEffect(() => {
    if (!doc || !sizes.length) return;
    const wanted = initialJump.current;
    if (wanted > 1) {
      requestAnimationFrame(() => goTo(wanted, false));
    } else if (reading?.position && reading.position.page > 1 && resumeOffer === null) {
      setResumeOffer(reading.position.page);
    }
    initialJump.current = 0;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc, sizes.length]);

  // Rolagem pela pessoa conta como navegação (salva a posição); a abertura, não.
  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const mark = () => {
      interacted.current = true;
      setResumeOffer((r) => (r ? null : r));
    };
    el.addEventListener("wheel", mark, { passive: true });
    el.addEventListener("touchmove", mark, { passive: true });
    return () => {
      el.removeEventListener("wheel", mark);
      el.removeEventListener("touchmove", mark);
    };
  }, [doc]);

  // Posição de retomada: separada das páginas lidas; só depois de navegar.
  useEffect(() => {
    if (!interacted.current || !pages) return;
    const t = window.setTimeout(() => {
      const known = reading?.position?.page;
      if (current === known || current === lastPositionSent.current) return;
      lastPositionSent.current = current;
      void enqueue("reading.position", entity.position(lesson.id, lesson.version), {
        lesson_id: lesson.id,
        version: lesson.version,
        page: current,
        pages,
      });
    }, 1500);
    return () => window.clearTimeout(t);
  }, [current, pages, lesson, enqueue, reading?.position?.page]);

  // Aviso único quando a última marcação completa a aula.
  useEffect(() => {
    if (!sync) return;
    if (completedBefore.current === false && complete) {
      toast(
        prefs.rpgEffects
          ? `Aula concluída: todas as ${pages} páginas marcadas. Mais um trecho do rumo percorrido.`
          : `Aula concluída: todas as ${pages} páginas marcadas.`,
        "rpg",
      );
    }
    completedBefore.current = complete;
  }, [complete, sync, pages, prefs.rpgEffects, toast]);

  const toggle = useCallback(
    (page: number, read: boolean) => {
      interacted.current = true;
      const token = ++markToken.current;
      setSavingMarks((marks) => new Map(marks).set(page, { read, token }));
      void enqueue("reading.page", entity.page(lesson.id, lesson.version, page), {
        lesson_id: lesson.id,
        version: lesson.version,
        page,
        pages: lesson.pages ?? pages,
        read,
      }).catch(() => toast("Não foi possível guardar a marcação neste navegador. Tente novamente.", "error")).finally(() => {
        setSavingMarks((marks) => {
          if (marks.get(page)?.token !== token) return marks;
          const next = new Map(marks);
          next.delete(page);
          return next;
        });
      });
    },
    [enqueue, lesson, pages, toast],
  );

  const markStatus = useCallback(
    (page: number): MarkStatus => {
      if (savingMarks.has(page)) return "guardando";
      const mark = reading?.marks.get(page);
      const ent = entity.page(lesson.id, lesson.version, page);
      if (sync?.conflicts.some((c) => c.envelope.entity_id === ent)) return "conflito";
      if (!mark) return null;
      if (mark.origin === "pending") return online ? "pendente" : "offline";
      return "salvo";
    },
    [reading, sync?.conflicts, lesson, online, savingMarks],
  );

  const registerRef = useCallback((page: number, el: HTMLElement | null) => {
    if (el) pageEls.current.set(page, el);
    else pageEls.current.delete(page);
  }, []);

  // Teclado: ←/→ e PageUp/PageDown trocam de página (fora de campos de texto).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(tag) || e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.key === "ArrowRight" || e.key === "PageDown") {
        e.preventDefault();
        goTo(current + 1);
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        goTo(current - 1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, goTo]);

  const notes = useMemo(
    () =>
      p
        ? [...p.notes.values()]
            .filter((n) => n.lessonId === lesson.id && n.version === lesson.version && !n.deleted)
            .sort((a, b) => (a.page ?? 0) - (b.page ?? 0) || a.at.localeCompare(b.at))
        : [],
    [p, lesson],
  );
  // Marcador de página: target_type "bookmark", identidade canônica do contrato.
  const bookmarkEntity = (page: number) => entity.favorite("bookmark", entity.bookmarkTarget(lesson.id, lesson.version, page), lesson.version);
  const bookmarks = useMemo(() => {
    if (!p || !pages) return [];
    const marked: number[] = [];
    for (let page = 1; page <= pages; page += 1) {
      if (p.favorites.get(bookmarkEntity(page))?.favorite) marked.push(page);
    }
    return marked;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [p, lesson, pages]);
  const bookmarked = bookmarks.includes(current);

  const saveNote = async (text: string, page: number | null, id?: string) => {
    await enqueue("note.save", id ?? uuid(), { lesson_id: lesson.id, question_id: null, version: lesson.version, page, text, deleted: false });
  };
  const deleteNote = async (note: NoteState) => {
    await enqueue("note.save", note.id, { lesson_id: lesson.id, question_id: null, version: lesson.version, page: note.page, text: note.text, deleted: true });
    toast("Nota excluída.");
  };
  const toggleBookmark = () =>
    void enqueue("favorite.set", bookmarkEntity(current), {
      target_type: "bookmark",
      target_id: entity.bookmarkTarget(lesson.id, lesson.version, current),
      version: lesson.version,
      favorite: !bookmarked,
    });

  const outline = pdfOutline.length ? pdfOutline : lesson.outline;
  const zoomBy = (delta: number) => setZoom({ mode: "livre", scale: Math.min(3, Math.max(0.5, Math.round((scale + delta) * 10) / 10)) });

  if (loadError) {
    return (
      <div className="page">
        {online ? (
          <ErrorState title="Não foi possível abrir o PDF" message="O arquivo não respondeu ou está corrompido. Suas marcações continuam salvas." onRetry={() => location.reload()} />
        ) : (
          <OfflineState what="O PDF" />
        )}
      </div>
    );
  }

  const currentRead = readSet.has(current);
  return (
    <div className="reader" data-paper={prefs.paper} data-panel={panel ? "open" : "closed"}>
      <header className="reader-top">
        <Link to={lessonPath(lesson)} className="icon-btn" aria-label="Voltar aos detalhes da aula">
          <ArrowLeft size={18} aria-hidden="true" />
        </Link>
        <div className="reader-title grow">
          <h1 className="truncate title reader-h1" title={lesson.title}>
            {lesson.title}
          </h1>
          <span className="xs muted truncate">
            {topicName(catalog, lesson.topicIds[0])} · {lesson.versionLabel} {lesson.example && <ExampleTag />}
          </span>
        </div>
        <div data-decor className="desktop-only">
          <StudyTimer timer={timer} category="Teoria" subjectId={lesson.subjectId} topicId={lesson.topicIds[0] ?? null} lesson={lesson} compact />
        </div>
      </header>

      <div className="reader-tools" role="toolbar" aria-label="Ferramentas do leitor">
        <div className="tool-group">
          <button type="button" className="icon-btn" onClick={() => goTo(current - 1)} disabled={current <= 1} aria-label="Página anterior">
            <ChevronLeft size={18} aria-hidden="true" />
          </button>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              goTo(Number(pageInput) || current);
            }}
            className="row"
          >
            <label className="sr-only" htmlFor="pagina-atual">
              Ir para a página
            </label>
            <input
              id="pagina-atual"
              className="input page-input tabular"
              inputMode="numeric"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value.replace(/\D/g, ""))}
              onBlur={() => setPageInput(String(current))}
            />
            <span className="small muted nowrap">de {pages || "…"}</span>
          </form>
          <button type="button" className="icon-btn" onClick={() => goTo(current + 1)} disabled={current >= pages} aria-label="Próxima página">
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="tool-group">
          <button type="button" className="icon-btn" onClick={() => zoomBy(-0.1)} aria-label="Diminuir zoom">
            <Minus size={16} aria-hidden="true" />
          </button>
          <span className="small tabular zoom-value" aria-live="polite">
            {Math.round(scale * 100)}%
          </span>
          <button type="button" className="icon-btn" onClick={() => zoomBy(0.1)} aria-label="Aumentar zoom">
            <Plus size={16} aria-hidden="true" />
          </button>
          <div className="segmented fit-toggle" role="group" aria-label="Ajuste">
            <button type="button" aria-pressed={zoom.mode === "largura"} onClick={() => setZoom({ mode: "largura", scale })}>
              Largura
            </button>
            <button type="button" aria-pressed={zoom.mode === "pagina"} onClick={() => setZoom({ mode: "pagina", scale })}>
              <Maximize2 size={14} aria-hidden="true" /> Página
            </button>
          </div>
        </div>

        <div className="tool-group">
          <button type="button" className="icon-btn" aria-pressed={bookmarked} onClick={toggleBookmark} aria-label={bookmarked ? `Remover marcador da página ${current}` : `Marcar página ${current}`} title="Marcador">
            <Bookmark size={18} aria-hidden="true" fill={bookmarked ? "currentColor" : "none"} />
          </button>
          <button
            type="button"
            className="icon-btn paper-toggle"
            aria-pressed={prefs.paper === "suave"}
            onClick={() => setPrefs({ paper: prefs.paper === "suave" ? "natural" : "suave" })}
            aria-label={prefs.paper === "suave" ? "Papel suave ligado (menos brilho, sem inverter imagens)" : "Papel natural"}
            title="Brilho do papel"
          >
            <SunDim size={18} aria-hidden="true" />
          </button>
          <div className="segmented" role="group" aria-label="Painel lateral">
            <button type="button" aria-pressed={panel === "indice"} onClick={() => setPanel(panel === "indice" ? null : "indice")} title="Índice">
              <ListTree size={14} aria-hidden="true" /> <span className="hide-sm">Índice</span>
            </button>
            <button type="button" aria-pressed={panel === "busca"} onClick={() => setPanel(panel === "busca" ? null : "busca")} title="Buscar">
              <Search size={14} aria-hidden="true" /> <span className="hide-sm">Buscar</span>
            </button>
            <button type="button" aria-pressed={panel === "notas"} onClick={() => setPanel(panel === "notas" ? null : "notas")} title="Notas">
              <NotebookPen size={14} aria-hidden="true" /> <span className="hide-sm">Notas</span>
              {notes.length > 0 && <span className="n">{notes.length}</span>}
            </button>
            <button type="button" aria-pressed={panel === "marcadores"} onClick={() => setPanel(panel === "marcadores" ? null : "marcadores")} title="Marcadores">
              <Bookmark size={14} aria-hidden="true" /> <span className="hide-sm">Marcadores</span>
            </button>
          </div>
        </div>
      </div>

      {mismatch && (
        <p className="notice warning reader-notice">
          Este PDF tem {doc!.numPages} páginas, mas o catálogo informa {lesson.pages}. As marcações seguem o catálogo; avise quem publica o conteúdo.
        </p>
      )}
      {older && !carryHidden && (
        <div className="notice reader-notice" role="status">
          <span className="grow">
            Você marcou {older.pages.length} páginas como lidas na versão {older.version}. Esta versão começa sem marcações; você pode trazê-las depois
            de conferir.
          </span>
          <button className="btn sm" type="button" onClick={() => setCarry(older)}>
            Trazer marcações
          </button>
          <button className="btn ghost sm" type="button" onClick={() => setCarryHidden(true)}>
            Agora não
          </button>
        </div>
      )}
      {resumeOffer && (
        <div className="notice reader-notice" role="status">
          <span className="grow">Você parou na página {resumeOffer}.</span>
          <button
            className="btn sm"
            type="button"
            onClick={() => {
              goTo(resumeOffer);
              setResumeOffer(null);
            }}
          >
            Ir para a página {resumeOffer}
          </button>
          <button className="btn ghost sm" type="button" onClick={() => setResumeOffer(0)}>
            Ficar no início
          </button>
        </div>
      )}

      <div className="reader-body">
        <div className="reader-scroll" ref={scroller} tabIndex={0} aria-label="Páginas do PDF">
          {!doc ? (
            <div style={{ padding: 24 }}>
              <Loading label="Abrindo o PDF…" />
            </div>
          ) : (
            sizes.map((size, i) => (
              <PageView
                key={i + 1}
                doc={doc}
                page={i + 1}
                scale={rounded}
                size={size}
                read={readSet.has(i + 1)}
                status={markStatus(i + 1)}
                disabled={!sync || i + 1 > (lesson.pages ?? sizes.length)}
                highlight={panel === "busca" ? query : ""}
                onToggle={toggle}
                registerRef={registerRef}
              />
            ))
          )}
        </div>

        {panel && doc && (
          <aside className="reader-panel" aria-label="Painel do leitor">
            <div className="row panel-head">
              <h2 className="grow">{{ indice: "Índice", busca: "Buscar no PDF", notas: "Notas", marcadores: "Marcadores" }[panel]}</h2>
              <button type="button" className="icon-btn sm" aria-label="Fechar painel" onClick={() => setPanel(null)}>
                <X size={16} aria-hidden="true" />
              </button>
            </div>
            {panel === "indice" && <OutlinePanel outline={outline} current={current} onGo={goTo} />}
            {panel === "busca" && <SearchPanel doc={doc} query={query} setQuery={setQuery} onGo={goTo} />}
            {panel === "notas" && (
              <NotesPanel
                notes={notes}
                current={current}
                onSave={saveNote}
                onDelete={deleteNote}
                onGo={goTo}
                onCard={(n) =>
                  setCardDraft({
                    subjectId: lesson.subjectId,
                    front: "",
                    back: n.text,
                    explanation: "",
                    source: `${lesson.title}${n.page ? `, p. ${n.page}` : ""}`,
                    lessonId: lesson.id,
                    questionId: null,
                  })
                }
              />
            )}
            {panel === "marcadores" && <BookmarksPanel pages={bookmarks} onGo={goTo} />}
          </aside>
        )}
      </div>

      <footer className="reader-bar" aria-label="Leitura da página atual">
        <span className="small nowrap">
          Página <strong className="tabular">{current}</strong> de {pages}
        </span>
        <label className={`check mark-box bar-box${currentRead ? " is-read" : ""}`} htmlFor="li-pagina-barra">
          <input id="li-pagina-barra" type="checkbox" checked={currentRead} disabled={!sync || !doc} onChange={(e) => toggle(current, e.target.checked)} />
          <span>
            Li esta página <span className="tabular faint">({current})</span>
          </span>
        </label>
        <MarkBadge status={markStatus(current)} />
        <span className="spacer" />
        <div className="mobile-only" data-decor>
          <StudyTimer timer={timer} category="Teoria" subjectId={lesson.subjectId} topicId={lesson.topicIds[0] ?? null} lesson={lesson} compact />
        </div>
        <div className="bar-progress">
          <span className="small tabular nowrap">
            {complete ? "Aula concluída · " : ""}
            {readSet.size} de {lesson.pages ?? pages} páginas marcadas como lidas
          </span>
          <ProgressBar value={readSet.size} max={lesson.pages ?? pages} label="Páginas marcadas como lidas" />
        </div>
      </footer>

      {carry && (
        <CarryDialog
          source={carry.version}
          target={lesson.version}
          initial={pageRanges(carry.pages)}
          limit={lesson.pages ?? pages}
          parse={parseRanges}
          onCancel={() => setCarry(null)}
          onConfirm={(chosen) => {
            for (const page of chosen) if (!readSet.has(page)) toggle(page, true);
            setCarry(null);
            toast(`${chosen.length} ${chosen.length === 1 ? "página marcada" : "páginas marcadas"} nesta versão.`);
          }}
        />
      )}
      {cardDraft && <CardEditor draft={cardDraft} title="Criar flashcard da nota" onClose={() => setCardDraft(null)} />}
    </div>
  );
}
