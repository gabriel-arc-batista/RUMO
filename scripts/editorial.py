"""Administrative CLI for reviewed batches; no remote access or credentials."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from editorial import Editorial


def main():
    parser = argparse.ArgumentParser(
        description="Editor RUMO — preparação local, sem publicação automática"
    )
    parser.add_argument(
        "--workspace",
        required=True,
        type=Path,
        help="SQLite editorial separado da base pessoal",
    )
    parser.add_argument(
        "--taxonomy",
        required=True,
        type=Path,
        help="JSON: ID do assunto → ID da disciplina",
    )
    parser.add_argument("--actor", required=True, help="Editor/revisor responsável")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("import", "correct"):
        commands.add_parser(name).add_argument("file", type=Path)
    commands.add_parser("list")
    commands.add_parser("approve").add_argument("id")
    prepare = commands.add_parser("prepare")
    prepare.add_argument("ids", nargs="+")
    prepare.add_argument("--output", required=True, type=Path)
    withdraw = commands.add_parser("withdraw")
    withdraw.add_argument("id")
    withdraw.add_argument("--reason", required=True)
    args = parser.parse_args()
    editor = Editorial(
        args.workspace, json.loads(args.taxonomy.read_text(encoding="utf-8"))
    )
    try:
        if args.command == "list":
            result = editor.items()
        elif args.command == "import":
            result = editor.import_batch(
                json.loads(args.file.read_text(encoding="utf-8")), args.actor
            )
        elif args.command == "correct":
            editor.correct(
                json.loads(args.file.read_text(encoding="utf-8")), args.actor
            )
            result = {"corrected": True, "review_required": True}
        elif args.command == "approve":
            editor.approve(args.id, args.actor)
            result = {"approved": args.id}
        elif args.command == "prepare":
            # Refuse overwrite before changing the workspace state.
            with args.output.open("x", encoding="utf-8") as output:
                try:
                    result = editor.prepare(args.ids, args.actor)
                    output.write(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
                    )
                except Exception:
                    args.output.unlink(missing_ok=True)
                    raise
            result = {"prepared": len(result["questions"]), "published": False}
        else:
            result = editor.withdraw(args.id, args.actor, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        editor.close()


if __name__ == "__main__":
    main()
