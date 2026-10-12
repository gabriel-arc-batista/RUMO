import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Shell } from "./components/Shell";
import { ErrorState, Loading, OfflineState } from "./components/ui";
import { useRumo } from "./service/store";
import { Home } from "./pages/Home";
import { Login, NewPassword, Recover } from "./pages/account/Auth";

const Library = lazy(() => import("./pages/campo/Library"));
const LessonDetail = lazy(() => import("./pages/campo/LessonDetail"));
const Reader = lazy(() => import("./pages/campo/Reader"));
const ArenaHub = lazy(() => import("./pages/arena/ArenaHub"));
const ArenaSession = lazy(() => import("./pages/arena/ArenaSession"));
const CardsHome = lazy(() => import("./pages/cards/CardsHome"));
const DeckView = lazy(() => import("./pages/cards/DeckView"));
const ReviewSession = lazy(() => import("./pages/cards/ReviewSession"));
const AccountPage = lazy(() => import("./pages/account/Account"));

function RequireAccount({ children }: { children: ReactNode }) {
  const { account, authReady } = useRumo();
  const location = useLocation();
  if (!authReady) return <PageLoading />;
  if (!account) return <Navigate to={`/entrar?volta=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  return <>{children}</>;
}

function PageLoading() {
  return (
    <div className="page">
      <Loading />
    </div>
  );
}

/** Estados do catálogo: carregando, sem conexão, erro. */
function CatalogGate({ children }: { children: ReactNode }) {
  const { catalog, online, reloadCatalog } = useRumo();
  if (catalog.status === "loading") return <PageLoading />;
  if (catalog.status === "error") {
    return (
      <div className="page">
        {online ? (
          <ErrorState title="Não foi possível carregar o conteúdo" message={catalog.message} onRetry={reloadCatalog} />
        ) : (
          <OfflineState what="O catálogo" />
        )}
      </div>
    );
  }
  return <>{children}</>;
}

function Guarded({ children }: { children: ReactNode }) {
  return (
    <RequireAccount>
      <CatalogGate>
        <Suspense fallback={<PageLoading />}>{children}</Suspense>
      </CatalogGate>
    </RequireAccount>
  );
}

function NotFound() {
  return (
    <div className="page">
      <ErrorState title="Página não encontrada" message="O endereço não existe ou mudou. Use a navegação para voltar a uma das áreas." />
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/entrar" element={<Login />} />
        <Route path="/conta/recuperar" element={<Recover />} />
        <Route path="/conta/nova-senha" element={<NewPassword />} />
        <Route element={<Shell />}>
          <Route index element={<Guarded><Home /></Guarded>} />
          <Route path="campo" element={<Guarded><Library /></Guarded>} />
          <Route path="campo/aula/:lessonId" element={<Guarded><LessonDetail /></Guarded>} />
          <Route path="campo/aula/:lessonId/ler" element={<Guarded><Reader /></Guarded>} />
          <Route path="arena" element={<Guarded><ArenaHub /></Guarded>} />
          <Route path="arena/sessao" element={<Guarded><ArenaSession /></Guarded>} />
          <Route path="flashcards" element={<Guarded><CardsHome /></Guarded>} />
          <Route path="flashcards/deck/:deckId" element={<Guarded><DeckView /></Guarded>} />
          <Route path="flashcards/revisar" element={<Guarded><ReviewSession /></Guarded>} />
          <Route path="conta" element={<RequireAccount><Suspense fallback={<PageLoading />}><AccountPage /></Suspense></RequireAccount>} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
