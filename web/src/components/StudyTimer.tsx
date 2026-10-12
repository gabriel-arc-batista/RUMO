import { Pause, Play, Square, Timer } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { clock, compactDuration, localDay } from "../lib/format";
import { readLocal, writeLocal } from "../lib/prefs";
import { uuid } from "../lib/ids";
import { useRumo } from "../service/store";
import { Confirm, Dialog } from "./ui";

export type Category = "Teoria" | "Questões" | "Revisão" | "Simulado";

interface Stored {
  id: string;
  seconds: number;
  runningSince: number | null;
}

/**
 * Cronômetro explícito (contrato: aba aberta não conta como estudo).
 * Só corre depois de "Iniciar", pausa sozinho quando a aba fica oculta e
 * só vira sessão depois de "Registrar". O id da sessão nasce no início e é
 * o mesmo das tentativas/revisões ligadas a ela.
 */
export function useStudyTimer(key: string) {
  const { account, backend } = useRumo();
  const storageKey = `rumo.timer.${backend.mode}:${account?.userId ?? "signed-out"}:${key}`;
  const [state, setState] = useState<Stored>(() => {
    const saved = readLocal<Stored>(storageKey, { id: uuid(), seconds: 0, runningSince: null });
    // A ausência após fechar/recarregar não entra no tempo de estudo.
    return { ...saved, runningSince: null };
  });
  const active = useRef(state);
  const [now, setNow] = useState(Date.now());
  const [autoPaused, setAutoPaused] = useState(false);

  const elapsed = state.seconds + (state.runningSince ? Math.floor((now - state.runningSince) / 1000) : 0);

  const save = useCallback(
    (next: Stored) => {
      active.current = next;
      setState(next);
      writeLocal(storageKey, next);
    },
    [storageKey],
  );

  const pause = useCallback(() => {
    setState((s) => {
      if (!s.runningSince) return s;
      const next = { ...s, seconds: s.seconds + Math.floor((Date.now() - s.runningSince) / 1000), runningSince: null };
      active.current = next;
      writeLocal(storageKey, next);
      return next;
    });
  }, [storageKey]);

  const start = useCallback(() => {
    setAutoPaused(false);
    setNow(Date.now());
    setState((s) => {
      const next = s.runningSince ? s : { ...s, runningSince: Date.now() };
      active.current = next;
      writeLocal(storageKey, { ...next, runningSince: null });
      return next;
    });
  }, [storageKey]);

  useEffect(() => {
    if (!state.runningSince) return;
    let checkpoint = Date.now();
    let lastTick = checkpoint;
    const persist = () => {
      if (active.current.id !== state.id || active.current.runningSince !== state.runningSince) return;
      const stamp = Date.now() - lastTick > 5000 ? lastTick : Date.now();
      writeLocal(storageKey, { ...state, seconds: state.seconds + Math.max(0, Math.floor((stamp - state.runningSince!) / 1000)), runningSince: null });
    };
    const tick = window.setInterval(() => {
      const stamp = Date.now();
      if (stamp - lastTick > 5000) {
        const paused = { ...state, seconds: state.seconds + Math.max(0, Math.floor((lastTick - state.runningSince!) / 1000)), runningSince: null };
        active.current = paused;
        setState(paused);
        writeLocal(storageKey, paused);
        setAutoPaused(true);
        return;
      }
      lastTick = stamp;
      setNow(stamp);
      if (stamp - checkpoint >= 5000) { persist(); checkpoint = stamp; }
    }, 1000);
    const hide = () => {
      if (document.visibilityState === "hidden") {
        pause();
        setAutoPaused(true);
      }
    };
    document.addEventListener("visibilitychange", hide);
    return () => {
      window.clearInterval(tick);
      document.removeEventListener("visibilitychange", hide);
      persist();
    };
  }, [state.runningSince, state.id, state.seconds, storageKey, pause]);

  const reset = useCallback(() => save({ id: uuid(), seconds: 0, runningSince: null }), [save]);

  return { sessionId: state.id, elapsed, running: Boolean(state.runningSince), autoPaused, start, pause, reset };
}

export type StudyTimerApi = ReturnType<typeof useStudyTimer>;

export function StudyTimer({
  timer,
  category,
  subjectId,
  topicId,
  lesson,
  compact,
}: {
  timer: StudyTimerApi;
  category: Category;
  subjectId: string;
  topicId: string | null;
  lesson?: { id: string; version: string };
  compact?: boolean;
}) {
  const { enqueue, toast, prefs } = useRumo();
  const [confirm, setConfirm] = useState(false);
  const [discard, setDiscard] = useState(false);
  const busy = useRef(false);

  const register = async () => {
    if (busy.current) return;
    busy.current = true;
    timer.pause();
    try {
      await enqueue("study.session", timer.sessionId, {
        plan_id: "site",
        subject_id: subjectId,
        topic_id: topicId,
        day: localDay(),
        category,
        elapsed: timer.elapsed,
        lesson_id: lesson?.id ?? null,
        lesson_version: lesson?.version ?? null,
      });
      toast(
        prefs.rpgEffects
          ? `Sessão de ${compactDuration(timer.elapsed)} registrada. O XP vem do serviço ao sincronizar.`
          : `Sessão de ${compactDuration(timer.elapsed)} registrada.`,
        "rpg",
      );
      timer.reset();
    } catch {
      toast("Não foi possível guardar a sessão. O tempo continua preservado neste navegador.", "error");
    } finally {
      busy.current = false;
      setConfirm(false);
    }
  };

  return (
    <div className={`timer${compact ? " compact" : ""}`} data-running={timer.running}>
      <Timer size={16} aria-hidden="true" className="faint" />
      <span className="tabular timer-value" aria-live="off" title="Tempo desta sessão (só conta com o cronômetro iniciado e a aba visível)">
        {clock(timer.elapsed)}
      </span>
      {timer.autoPaused && !timer.running && <span className="xs muted">pausado: aba oculta</span>}
      {timer.running ? (
        <button type="button" className="icon-btn sm" onClick={timer.pause} aria-label="Pausar cronômetro">
          <Pause size={16} aria-hidden="true" />
        </button>
      ) : (
        <button type="button" className="btn sm" onClick={timer.start}>
          <Play size={14} aria-hidden="true" /> {timer.elapsed ? "Retomar" : "Iniciar estudo"}
        </button>
      )}
      {timer.elapsed >= 60 && (
        <button type="button" className="icon-btn sm" onClick={() => setConfirm(true)} aria-label="Encerrar e registrar sessão">
          <Square size={14} aria-hidden="true" />
        </button>
      )}
      {confirm && (
        <Dialog
          title="Registrar sessão de estudo"
          onClose={() => setConfirm(false)}
          actions={
            <>
              <button className="btn danger" type="button" onClick={() => setDiscard(true)}>
                Descartar tempo
              </button>
              <button className="btn" type="button" onClick={() => setConfirm(false)}>
                Continuar estudando
              </button>
              <button className="btn primary" type="button" onClick={() => void register()} data-autofocus>
                Registrar {compactDuration(timer.elapsed)}
              </button>
            </>
          }
        >
          <p className="muted">
            {compactDuration(timer.elapsed)} de {category.toLowerCase()} entram no seu histórico e aparecem no aplicativo depois da sincronização. Pausas e tempo com a aba oculta não contam.
          </p>
        </Dialog>
      )}
      {discard && (
        <Confirm
          title="Descartar o tempo desta sessão?"
          message={`Os ${compactDuration(timer.elapsed)} cronometrados não serão registrados. Respostas e marcações já feitas continuam salvas.`}
          confirmLabel="Descartar tempo"
          onCancel={() => setDiscard(false)}
          onConfirm={() => {
            timer.reset();
            setDiscard(false);
            setConfirm(false);
          }}
        />
      )}
    </div>
  );
}
