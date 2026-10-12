import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import type { Backend } from "./service/backend";
import { createBackend } from "./service/config";
import { RumoProvider } from "./service/store";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/layout.css";
import "./styles/ui.css";
import "./styles/pages.css";

const root = createRoot(document.getElementById("root")!);
let backend: Backend | null = null;
let problem = "";
try {
  backend = createBackend();
} catch (error) {
  problem = error instanceof Error ? error.message : String(error);
}

root.render(
  <StrictMode>
    {backend ? (
      <RumoProvider backend={backend}>
        <App />
      </RumoProvider>
    ) : (
      // Configuração inválida (ex.: chave privilegiada): não abre nada contra o serviço.
      <main className="auth" id="conteudo">
        <div className="auth-card" role="alert">
          <h1>Configuração inválida</h1>
          <p className="muted">O site não foi configurado com uma chave pública válida do serviço. {problem}</p>
        </div>
      </main>
    )}
  </StrictMode>,
);
