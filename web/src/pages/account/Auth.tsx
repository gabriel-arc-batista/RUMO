import { Compass, MailCheck } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ExampleTag, Segmented } from "../../components/ui";
import { useRumo } from "../../service/store";

function AuthLayout({ title, subtitle, children }: { title: string; subtitle: ReactNode; children: ReactNode }) {
  const { backend } = useRumo();
  return (
    <main className="auth" id="conteudo">
      <div className="auth-card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <span className="brand" style={{ padding: 0 }}>
            <Compass size={22} aria-hidden="true" /> <span>RUMO</span>
          </span>
          {backend.mode === "exemplo" && <ExampleTag title="Modo exemplo: conta simulada neste navegador." />}
        </div>
        <div className="stack" style={{ gap: 6 }}>
          <h1>{title}</h1>
          <p className="muted">{subtitle}</p>
        </div>
        {children}
      </div>
    </main>
  );
}

function message(error: unknown): string {
  const text = error instanceof Error ? error.message : String(error);
  if (/invalid login|invalid_credentials|senha incorreta/i.test(text)) return "E-mail ou senha incorretos.";
  if (/email not confirmed/i.test(text)) return "Confirme o e-mail pelo link que enviamos antes de entrar.";
  if (/already registered|already been registered/i.test(text)) return "Já existe uma conta com este e-mail. Use “Entrar”.";
  if (/password/i.test(text) && /6|8|short|weak/i.test(text)) return "A senha precisa ter pelo menos 8 caracteres.";
  if (/fetch|network/i.test(text)) return "Sem conexão com o serviço. Tente de novo quando a internet voltar.";
  return "Não foi possível concluir agora. Tente de novo em instantes.";
}

export function Login() {
  const { backend, account } = useRumo();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const back = params.get("volta") || "/";
  const [mode, setMode] = useState<"entrar" | "criar">("entrar");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmSent, setConfirmSent] = useState(false);

  useEffect(() => {
    if (account) navigate(back.startsWith("/") ? back : "/", { replace: true });
  }, [account, back, navigate]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("A senha precisa ter pelo menos 8 caracteres.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "entrar") await backend.auth.signIn(email, password);
      else {
        const { needsConfirmation } = await backend.auth.signUp(email, password);
        if (needsConfirmation) setConfirmSent(true);
      }
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  };

  if (confirmSent) {
    return (
      <AuthLayout title="Confirme seu e-mail" subtitle={`Enviamos um link para ${email}. Abra-o neste dispositivo para ativar a conta.`}>
        <MailCheck size={32} className="faint" aria-hidden="true" />
        <button className="btn" type="button" onClick={() => setConfirmSent(false)}>
          Voltar para entrar
        </button>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title={mode === "entrar" ? "Entrar no RUMO" : "Criar conta"}
      subtitle={
        backend.mode === "exemplo"
          ? "Modo exemplo: qualquer e-mail e uma senha com 8 caracteres criam uma conta simulada, guardada só neste navegador."
          : "A mesma conta do aplicativo. O aplicativo continua funcionando sem conta; aqui ela guarda seu progresso no site."
      }
    >
      <Segmented
        label="Entrar ou criar conta"
        value={mode}
        onChange={(v) => {
          setMode(v);
          setError(null);
        }}
        options={[
          { value: "entrar", label: "Entrar" },
          { value: "criar", label: "Criar conta" },
        ]}
      />
      <form className="stack" onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="email">E-mail</label>
          <input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="senha">Senha</label>
          <input
            id="senha"
            className="input"
            type="password"
            autoComplete={mode === "entrar" ? "current-password" : "new-password"}
            required
            minLength={8}
            value={password}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? "auth-erro" : "senha-dica"}
            onChange={(e) => setPassword(e.target.value)}
          />
          {mode === "criar" && (
            <span className="hint" id="senha-dica">
              Pelo menos 8 caracteres.
            </span>
          )}
        </div>
        {error && (
          <p className="notice error" id="auth-erro" role="alert">
            {error}
          </p>
        )}
        <button className="btn primary lg" type="submit" disabled={busy || !email}>
          {busy ? "Aguarde…" : mode === "entrar" ? "Entrar" : "Criar conta"}
        </button>
      </form>
      {mode === "entrar" && (
        <Link to="/conta/recuperar" className="small">
          Esqueci minha senha
        </Link>
      )}
    </AuthLayout>
  );
}

export function Recover() {
  const { backend } = useRumo();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await backend.auth.requestReset(email);
      setSent(true);
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <AuthLayout
      title="Recuperar acesso"
      subtitle={sent ? `Se houver uma conta para ${email}, você vai receber um link para criar uma nova senha.` : "Informe o e-mail da conta. Enviaremos um link para criar uma nova senha."}
    >
      {!sent && (
        <form className="stack" onSubmit={submit}>
          <div className="field">
            <label htmlFor="email-rec">E-mail</label>
            <input id="email-rec" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          {error && (
            <p className="notice error" role="alert">
              {error}
            </p>
          )}
          <button className="btn primary lg" type="submit" disabled={busy || !email}>
            {busy ? "Enviando…" : "Enviar link"}
          </button>
        </form>
      )}
      <Link to="/entrar" className="small">
        Voltar para entrar
      </Link>
    </AuthLayout>
  );
}

export function NewPassword() {
  const { backend } = useRumo();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError("A senha precisa ter pelo menos 8 caracteres.");
      return;
    }
    setBusy(true);
    try {
      await backend.auth.updatePassword(password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <AuthLayout title="Nova senha" subtitle="Escolha uma senha nova para a sua conta.">
      <form className="stack" onSubmit={submit}>
        <div className="field">
          <label htmlFor="nova">Nova senha</label>
          <input id="nova" className="input" type="password" autoComplete="new-password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
          <span className="hint">Pelo menos 8 caracteres.</span>
        </div>
        {error && (
          <p className="notice error" role="alert">
            {error}
          </p>
        )}
        <button className="btn primary lg" type="submit" disabled={busy}>
          {busy ? "Salvando…" : "Salvar nova senha"}
        </button>
      </form>
    </AuthLayout>
  );
}
