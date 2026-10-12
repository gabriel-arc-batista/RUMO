"""Fail closed on sensitive tracked files; never print matching secret values."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {
    "validation",
    "build",
    "dist",
    "tools",
    "backups",
    ".venv",
    "__pycache__",
}
FORBIDDEN_SUFFIXES = {".sqlite3", ".db", ".log", ".pem", ".key", ".pfx", ".p12", ".pyc"}
PATTERNS = {
    "private key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    ),
    "GitHub token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "OpenAI key": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b"),
    "Supabase secret key": re.compile(r"\bsb_secret_[A-Za-z0-9_-]{24,}\b"),
}


def main():
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    names = [s.decode("utf-8") for s in result.stdout.split(b"\0") if s]
    if not names:
        raise SystemExit("No tracked files to review.")
    failures = []
    for name in names:
        path = Path(name)
        if (
            set(path.parts) & FORBIDDEN_PARTS
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
            or any(p == ".env" or p.startswith(".env.") for p in path.parts)
        ):
            failures.append((name, "sensitive/generated file"))
        if path.suffix.lower() in {
            ".py",
            ".md",
            ".json",
            ".txt",
            ".toml",
            ".yml",
            ".yaml",
            ".ts",
            ".tsx",
            ".js",
            ".mjs",
        }:
            text = (ROOT / path).read_text(encoding="utf-8")
            failures.extend(
                (name, label)
                for label, pattern in PATTERNS.items()
                if pattern.search(text)
            )
    if failures:
        for name, label in failures:
            print(f"Rejected: {name} ({label})")
        raise SystemExit(1)
    print(
        f"Reviewed {len(names)} tracked files: no prohibited files or recognized secret patterns."
    )


if __name__ == "__main__":
    main()
