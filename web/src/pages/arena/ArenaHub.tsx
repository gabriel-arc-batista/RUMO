import { Swords } from "lucide-react";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { EmptyState, ExampleTag, Segmented } from "../../components/ui";
import { plural } from "../../lib/format";
import { useCatalog, useRumo } from "../../service/store";
import { lastAttempt, MODES, readFilters, realMetadata, selectQuestions, toParams, type Filters, type Mode } from "./arena";

export default function ArenaHub() {
  const catalog = useCatalog();
  const { sync } = useRumo();
  const [params, setParams] = useSearchParams();
  const f = readFilters(params);
  const p = sync?.projection;
  const meta = realMetadata(catalog);
  const update = (patch: Partial<Filters>) => setParams(toParams({ ...f, ...patch }), { replace: true });

  const selected = useMemo(() => selectQuestions(catalog, p, f), [catalog, p, f]);
  const topics = catalog.topics.filter((t) => !f.subject || t.subjectId === f.subject);
  const countFor = (mode: Mode) => selectQuestions(catalog, p, { ...f, mode }).length;

  const attempts = p ? [...p.attempts.values()] : [];
  const wrongNow = catalog.questions.filter((q) => lastAttempt(p, q.id)?.result?.status === "incorrect").length;

  if (!catalog.questions.length) {
    return (
      <div className="page">
        <ArenaHead />
        <EmptyState icon={<Swords size={28} aria-hidden="true" />} title="Ainda não há questões publicadas">
          A Arena abre quando houver questões revisadas no catálogo, com gabarito e procedência conferidos.
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="page">
      <ArenaHead />

      <section className="arena-setup surface" aria-labelledby="escolha">
        <h2 id="escolha" className="sr-only">
          Escolher questões
        </h2>
        <div className="setup-grid">
          <div className="field">
            <label htmlFor="materia">Matéria</label>
            <select id="materia" className="select" value={f.subject} onChange={(e) => update({ subject: e.target.value, topic: "" })}>
              <option value="">Todas as matérias</option>
              {catalog.subjects
                .filter((s) => catalog.questions.some((q) => q.subjectId === s.id))
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="assunto">Assunto</label>
            <select id="assunto" className="select" value={f.topic} onChange={(e) => update({ topic: e.target.value })}>
              <option value="">Todos os assuntos</option>
              {topics
                .filter((t) => catalog.questions.some((q) => q.topicIds.includes(t.id)))
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="edital">Edital-alvo</label>
            <select id="edital" className="select" value={f.exam} onChange={(e) => update({ exam: e.target.value })}>
              <option value="">Todos os editais</option>
              {catalog.exams.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </div>
          {meta.banks.length > 0 && (
            <div className="field">
              <label htmlFor="banca">Banca</label>
              <select id="banca" className="select" value={f.bank} onChange={(e) => update({ bank: e.target.value })}>
                <option value="">Todas</option>
                {meta.banks.map((b) => (
                  <option key={b}>{b}</option>
                ))}
              </select>
            </div>
          )}
          {meta.years.length > 0 && (
            <div className="field">
              <label htmlFor="ano">Ano</label>
              <select id="ano" className="select" value={f.year} onChange={(e) => update({ year: e.target.value })}>
                <option value="">Todos</option>
                {meta.years.map((y) => (
                  <option key={y}>{y}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="stack" style={{ gap: "var(--s2)" }}>
          <span className="label small muted" id="modo-label">
            Modo de prática
          </span>
          <Segmented<Mode>
            label="Modo de prática"
            value={f.mode}
            onChange={(mode) => update({ mode })}
            options={MODES.map((m) => ({ value: m.value, label: m.label, count: countFor(m.value) }))}
          />
          <p className="xs faint">{MODES.find((m) => m.value === f.mode)?.hint}</p>
        </div>

        <div className="row wrap" style={{ justifyContent: "space-between" }}>
          <span className="small muted">
            {selected.length ? plural(selected.length, "questão selecionada", "questões selecionadas") : "Nenhuma questão com estes filtros."}
            {selected.some((q) => q.example) && (
              <>
                {" "}
                <ExampleTag />
              </>
            )}
          </span>
          {selected.length > 0 ? (
            <Link to={`/arena/sessao?${toParams(f).toString()}`} className="btn primary lg">
              <Swords size={18} aria-hidden="true" /> Entrar na Arena
            </Link>
          ) : (
            <button type="button" className="btn" onClick={() => setParams({}, { replace: true })}>
              Limpar filtros
            </button>
          )}
        </div>
      </section>

      <section className="stat-row" aria-label="Seu histórico na Arena">
        <div className="stat">
          <span className="value">{attempts.length}</span>
          <span className="label">respostas registradas</span>
        </div>
        <div className="stat">
          <span className="value">{attempts.filter((a) => a.result?.status === "correct").length}</span>
          <span className="label">acertos</span>
        </div>
        <div className="stat">
          <span className="value">{wrongNow}</span>
          <span className="label">questões para revanche</span>
        </div>
      </section>
      <p className="xs faint">Números das suas respostas, não uma medida de domínio: poucas tentativas não dizem quanto você sabe de um assunto.</p>
    </div>
  );
}

function ArenaHead() {
  return (
    <div className="page-head arena-head">
      <div className="titles">
        <h1>Arena</h1>
        <p>Escolha o assunto, leia com calma e confirme a resposta quando tiver certeza.</p>
      </div>
      <span className="arena-emblem" data-decor aria-hidden="true">
        <Swords size={26} />
      </span>
    </div>
  );
}
