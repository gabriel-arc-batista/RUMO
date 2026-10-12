import { MoreHorizontal, Pause, Pencil, Play, Trash2 } from "lucide-react";
import { useState } from "react";
import { Confirm, ExampleTag, Menu } from "../../components/ui";
import { relativeDay } from "../../lib/format";
import { useRumo } from "../../service/store";
import { CardEditor } from "./CardEditor";
import type { CardView } from "./useCards";

export function statusTag(v: CardView) {
  if (v.unsynced) return <span className="tag">Aguardando sincronização</span>;
  switch (v.status) {
    case "novo":
      return <span className="tag info">Novo</span>;
    case "vencido":
      return <span className="tag gold">Para revisar</span>;
    case "suspenso":
      return <span className="tag">Suspenso</span>;
    default:
      return <span className="tag">Volta {v.dueAt ? relativeDay(v.dueAt) : "em breve"}</span>;
  }
}

export function CardRow({ view, deckTitle }: { view: CardView; deckTitle?: string }) {
  const { enqueue, toast } = useRumo();
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(false);
  const { card } = view;

  const save = (patch: { suspended?: boolean; deleted?: boolean }) =>
    enqueue("card.save", card.id, {
      deck_id: card.deckId,
      front: card.front,
      back: card.back,
      explanation: card.explanation,
      source: card.source,
      lesson_id: card.lessonId,
      question_id: card.questionId,
      suspended: patch.suspended ?? card.suspended,
      deleted: patch.deleted ?? false,
    });

  return (
    <li className="list-row card-row">
      <div className="grow stack" style={{ gap: 4 }}>
        <span className="title card-front">{card.front}</span>
        <span className="row wrap meta">
          {statusTag(view)}
          {deckTitle && <span className="xs">{deckTitle}</span>}
          {card.personal ? <span className="xs faint">pessoal</span> : card.example && <ExampleTag />}
        </span>
      </div>
      {card.personal && (
        <Menu
          label={`Ações do cartão “${card.front.slice(0, 40)}”`}
          icon={<MoreHorizontal size={16} aria-hidden="true" />}
          items={[
            { label: "Editar", icon: <Pencil size={14} aria-hidden="true" />, onSelect: () => setEditing(true) },
            card.suspended
              ? {
                  label: "Reativar nas revisões",
                  icon: <Play size={14} aria-hidden="true" />,
                  onSelect: () => void save({ suspended: false }).then(() => toast("Cartão reativado.")),
                }
              : {
                  label: "Suspender das revisões",
                  icon: <Pause size={14} aria-hidden="true" />,
                  onSelect: () => void save({ suspended: true }).then(() => toast("Cartão suspenso: ele não aparece nas revisões até ser reativado.")),
                },
            { label: "Excluir", icon: <Trash2 size={14} aria-hidden="true" />, danger: true, onSelect: () => setRemoving(true) },
          ]}
        />
      )}
      {editing && (
        <CardEditor
          draft={{
            id: card.id,
            deckId: card.deckId,
            front: card.front,
            back: card.back,
            explanation: card.explanation,
            source: card.source,
            lessonId: card.lessonId,
            questionId: card.questionId,
            suspended: card.suspended,
          }}
          onClose={() => setEditing(false)}
        />
      )}
      {removing && (
        <Confirm
          title="Excluir este cartão?"
          message={`“${card.front.slice(0, 90)}${card.front.length > 90 ? "…" : ""}” sai dos seus cartões aqui e no aplicativo. O histórico de revisões já feitas é preservado no serviço. Para só pausar, use “Suspender”.`}
          confirmLabel="Excluir cartão"
          onCancel={() => setRemoving(false)}
          onConfirm={() => {
            setRemoving(false);
            void save({ deleted: true }).then(() => toast("Cartão excluído."));
          }}
        />
      )}
    </li>
  );
}
