import { BookOpen, Compass, Focus, Home, Layers, Swords, UserRound, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useRumo } from "../service/store";
import { useDueCount } from "../pages/cards/useCards";
import { SyncPanel, SyncPill } from "./Sync";
import { ExampleTag, Portrait, ProgressBar } from "./ui";

const AREAS = [
  { to: "/", label: "Início", icon: Home, end: true },
  { to: "/campo", label: "Campo de Treinamento", short: "Campo", icon: BookOpen },
  { to: "/arena", label: "Arena", icon: Swords },
  { to: "/flashcards", label: "Flashcards", short: "Cartões", icon: Layers },
];

export function Shell() {
  const { prefs, setPrefs, backend, toasts, closeToast, account, progress } = useRumo();
  const [panel, setPanel] = useState(false);
  const due = useDueCount();
  const location = useLocation();
  const focus = prefs.focus;

  return (
    <div className="shell" data-focus={focus ? "on" : "off"}>
      <a className="skip-link" href="#conteudo">
        Pular para o conteúdo
      </a>
      <aside className="sidebar" aria-label="Navegação principal">
        <NavLink to="/" className="brand" aria-label="RUMO — início">
          <Compass size={22} aria-hidden="true" />
          <span>RUMO</span>
        </NavLink>
        <nav className="nav" aria-label="Áreas">
          <span className="nav-label">Estudo</span>
          {AREAS.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} title={label}>
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
              {to === "/flashcards" && due > 0 && (
                <span className="count" aria-label={`${due} cartões para revisar`}>
                  {due}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <nav className="nav" aria-label="Você">
          <span className="nav-label">Você</span>
          <NavLink to="/conta" title="Conta e progresso">
            <UserRound size={18} aria-hidden="true" />
            <span>Conta e progresso</span>
          </NavLink>
        </nav>
        <div className="sidebar-foot" data-decor>
          <NavLink to="/conta" className="char-card" aria-label="Seu viajante: ver progresso">
            <Portrait size={40} />
            <span className="hide-rail stack grow" style={{ gap: 4 }}>
              <span className="name">Viajante</span>
              {progress ? (
                <>
                  <span className="xs muted tabular">
                    Nível {progress.level} · {progress.xp}/{progress.xp_next} XP
                  </span>
                  <ProgressBar value={progress.xp} max={progress.xp_next} label={`XP no nível ${progress.level}`} />
                </>
              ) : (
                <span className="xs muted">{account ? "Progresso ao sincronizar" : "Entre para registrar"}</span>
              )}
            </span>
          </NavLink>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <NavLink to="/" className="brand mobile-brand" aria-label="RUMO — início">
            <Compass size={20} aria-hidden="true" />
            <span>RUMO</span>
          </NavLink>
          <div className="spacer" />
          {backend.mode === "exemplo" && (
            <ExampleTag title="Modo exemplo: serviço não configurado. Dados identificados, guardados só neste navegador." />
          )}
          {account && <SyncPill onOpen={() => setPanel(true)} />}
          <button
            type="button"
            className="icon-btn"
            aria-pressed={focus}
            aria-label={focus ? "Sair do modo foco" : "Modo foco: esconder navegação e personagem"}
            title={focus ? "Sair do modo foco" : "Modo foco"}
            onClick={() => setPrefs({ focus: !focus })}
          >
            <Focus size={18} aria-hidden="true" />
          </button>
          <NavLink to="/conta" className="icon-btn mobile-only" aria-label="Conta e progresso">
            <UserRound size={18} aria-hidden="true" />
          </NavLink>
          {focus && location.pathname !== "/" && (
            <NavLink to="/" className="btn ghost sm">
              Início
            </NavLink>
          )}
        </header>
        <main id="conteudo" tabIndex={-1}>
          <Outlet />
        </main>
      </div>

      <nav className="bottom-nav" aria-label="Áreas">
        {AREAS.map(({ to, label, short, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} aria-label={label}>
            <Icon size={20} aria-hidden="true" />
            <span>{short ?? label}</span>
          </NavLink>
        ))}
      </nav>

      {panel && <SyncPanel onClose={() => setPanel(false)} />}

      <div className="toasts" aria-live="polite" role="status">
        {toasts.map((t) => (
          <div key={t.id} className="toast">
            <span className="grow">{t.text}</span>
            <button type="button" className="icon-btn sm" aria-label="Fechar aviso" onClick={() => closeToast(t.id)}>
              <X size={14} aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
