import { LogOut, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SyncPanel, syncLabel } from "../../components/Sync";
import { Confirm, EquippedItems, ExampleTag, Portrait, ProgressBar, Segmented } from "../../components/ui";
import { useCharacter } from "../../service/useCharacter";
import { siteXp } from "../../domain/describe";
import { compactDuration, relativeDay } from "../../lib/format";
import type { Prefs } from "../../lib/prefs";
import { useRumo } from "../../service/store";

const SHARED = [
  "Páginas marcadas como lidas e a posição de retomada de cada aula",
  "Notas, favoritos e marcadores",
  "Respostas da Arena e o resultado calculado pelo serviço",
  "Cartões pessoais e o histórico de revisões",
  "Sessões de estudo registradas aqui com o cronômetro",
  "Do aplicativo para o site: aparência, nome e itens equipados do personagem",
  "Do aplicativo para o site: o ciclo de estudos atual, só para consulta",
];

const NOT_SHARED = [
  "Edital, metas e edição do ciclo (o ciclo só é exibido)",
  "Inventário completo, compras e moedas gastas",
  "Histórico antigo do aplicativo (só o que você escolher) e PDFs pessoais",
];

export default function AccountPage() {
  const { account, backend, sync, prefs, setPrefs, syncNow, progress } = useRumo();
  const character = useCharacter();
  const navigate = useNavigate();
  const [leaving, setLeaving] = useState(false);
  const [panel, setPanel] = useState(false);
  const [offline, setOffline] = useState(() => backend.isSimulatedOffline?.() ?? false);
  const p = sync?.projection;
  const pendingSessions = p ? siteXp(p).pendingSessions : 0;
  const sessions = p ? [...p.sessions.values()].sort((a, b) => b.at.localeCompare(a.at)).slice(0, 8) : [];

  const signOut = async () => {
    // Sai da página protegida antes: ao entrar de novo, a pessoa volta ao início.
    navigate("/entrar", { replace: true });
    await backend.auth.signOut();
  };

  const pref = <K extends keyof Prefs>(key: K, value: Prefs[K]) => setPrefs({ [key]: value } as Partial<Prefs>);

  return (
    <div className="page">
      <div className="page-head">
        <div className="titles">
          <h1>Conta e progresso</h1>
          <p>{account?.email}</p>
        </div>
        {backend.mode === "exemplo" && <ExampleTag title="Conta simulada neste navegador." />}
      </div>

      <div className="account-grid">
        <section className="surface stack" aria-labelledby="viajante">
          <div className="row" style={{ gap: "var(--s4)" }}>
            <span data-decor>
              <Portrait size={72} look={character.look} />
            </span>
            <div className="stack" style={{ gap: 4 }}>
              <h2 id="viajante" className="display-name">
                {character.name}
              </h2>
              <span className="small muted">
                {character.synced
                  ? "Aparência e equipamentos vindos do aplicativo."
                  : "Aparência padrão: conecte o aplicativo à mesma conta para ver a sua."}
              </span>
              <EquippedItems ids={character.equipped} max={8} />
            </div>
          </div>
          {progress ? (
            <div className="stack" style={{ gap: 6 }}>
              <div className="stat-row">
                <div className="stat">
                  <span className="value">{progress.level}</span>
                  <span className="label">nível na conta</span>
                </div>
                <div className="stat">
                  <span className="value tabular">
                    {progress.xp}/{progress.xp_next}
                  </span>
                  <span className="label">XP para o próximo nível</span>
                </div>
                <div className="stat">
                  <span className="value">{progress.coins}</span>
                  <span className="label">moedas ganhas</span>
                </div>
                <div className="stat">
                  <span className="value">{progress.victories ?? 0}</span>
                  <span className="label">vitórias na Arena</span>
                </div>
              </div>
              <ProgressBar value={progress.xp} max={progress.xp_next} label={`XP no nível ${progress.level}`} />
            </div>
          ) : (
            <p className="small muted">O nível aparece depois da primeira sincronização.</p>
          )}
          <p className="xs faint">
            Calculado pelo serviço a partir das sessões sincronizadas (site e aplicativo conectado): um XP por minuto líquido, como no aplicativo. Ler, repetir questões ou revisar sem sessão registrada não gera XP. Vitórias contam questões diferentes vencidas ao menos uma vez; repetir não soma nem dá XP. Inventário e compras continuam no aplicativo.
          </p>
          {pendingSessions > 0 && <p className="small">{pendingSessions} sessão(ões) aguardando o serviço.</p>}
          {sessions.length > 0 && (
            <ul className="list">
              {sessions.map((s) => (
                <li key={s.id} className="list-row" style={{ minHeight: 44, padding: "var(--s2) 0" }}>
                  <span className="grow small">
                    {s.payload.category} · {compactDuration(s.payload.elapsed)}
                  </span>
                  <span className="xs muted">{s.result ? `+${s.result.xp} XP` : "aguardando"}</span>
                  <span className="xs faint">{relativeDay(s.at)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="surface stack" aria-labelledby="sincronizacao">
          <h2 id="sincronizacao">Sincronização com o aplicativo</h2>
          <p>
            <strong>{syncLabel(sync?.state, sync?.pending ?? 0)}</strong>
            {sync?.lastSyncedAt && <span className="muted small"> · {relativeDay(sync.lastSyncedAt)}</span>}
          </p>
          <div className="row wrap">
            <button className="btn" type="button" onClick={() => void syncNow()}>
              <RefreshCw size={16} aria-hidden="true" /> Sincronizar agora
            </button>
            <button className="btn ghost" type="button" onClick={() => setPanel(true)}>
              Detalhes e conflitos
            </button>
          </div>
          <div className="two-col">
            <div>
              <h3 className="small">Compartilhado com o aplicativo</h3>
              <ul className="bullets small">
                {SHARED.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="small">Não sincronizado nesta versão</h3>
              <ul className="bullets small muted">
                {NOT_SHARED.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          </div>
          <p className="xs faint">O aplicativo continua funcionando sem conta. Para ver no aplicativo o que fez aqui, conecte a mesma conta nele.</p>
          {backend.mode === "exemplo" && (
            <label className="check small">
              <input
                type="checkbox"
                checked={offline}
                onChange={(e) => {
                  setOffline(e.target.checked);
                  backend.simulateOffline?.(e.target.checked);
                  void syncNow();
                }}
              />
              Simular queda de conexão (modo exemplo)
            </label>
          )}
        </section>

        <section className="surface stack" aria-labelledby="preferencias">
          <h2 id="preferencias">Preferências deste navegador</h2>
          <div className="pref">
            <span className="small">Movimento</span>
            <Segmented
              label="Movimento"
              value={prefs.motion}
              onChange={(v) => pref("motion", v)}
              options={[
                { value: "system", label: "Do sistema" },
                { value: "reduce", label: "Reduzido" },
                { value: "full", label: "Normal" },
              ]}
            />
          </div>
          <label className="check">
            <input type="checkbox" checked={prefs.rpgEffects} onChange={(e) => pref("rpgEffects", e.target.checked)} />
            Mensagens curtas da jornada (RPG) ao acertar, concluir e revisar
          </label>
          <label className="check">
            <input type="checkbox" checked={prefs.focus} onChange={(e) => pref("focus", e.target.checked)} />
            Modo foco: esconder navegação e personagem
          </label>
          <label className="check">
            <input type="checkbox" checked={prefs.arenaTimer} onChange={(e) => pref("arenaTimer", e.target.checked)} />
            Mostrar o cronômetro na Arena
          </label>
          <label className="check">
            <input type="checkbox" checked={prefs.paper === "suave"} onChange={(e) => pref("paper", e.target.checked ? "suave" : "natural")} />
            Papel suave no leitor (menos brilho, sem inverter imagens)
          </label>
        </section>

        <section className="surface stack" aria-labelledby="sessao">
          <h2 id="sessao">Sessão</h2>
          <p className="small muted">Sair desconecta este navegador da conta. O que já foi sincronizado continua na conta e no aplicativo.</p>
          <div>
            <button className="btn danger" type="button" onClick={() => setLeaving(true)}>
              <LogOut size={16} aria-hidden="true" /> Sair da conta
            </button>
          </div>
        </section>
      </div>

      {panel && <SyncPanel onClose={() => setPanel(false)} />}
      {leaving && (
        <Confirm
          title="Sair da conta neste navegador?"
          message={
            sync && sync.pending > 0
              ? `${sync.pending} ${sync.pending === 1 ? "ação ainda não foi enviada" : "ações ainda não foram enviadas"}. Elas ficam guardadas neste navegador e são enviadas quando você entrar de novo com ${account?.email}.`
              : `Você sai de ${account?.email} neste navegador. Nada é apagado da conta.`
          }
          confirmLabel="Sair da conta"
          onCancel={() => setLeaving(false)}
          onConfirm={() => void signOut()}
        />
      )}
    </div>
  );
}
