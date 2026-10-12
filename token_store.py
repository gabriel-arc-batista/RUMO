"""Opt-in "manter conectado": guarda somente o refresh token da conta.

Windows: cifrado com a DPAPI do usuário atual (CryptProtectData), sem dependências.
Outros sistemas: arquivo com permissão 0600 no diretório de dados, mesmo modelo
de CLIs como gh/supabase. Senha e access token nunca são gravados. "Sair" apaga.
"""

import base64
import json
import os
import sys
from pathlib import Path

VERSION = 1


def _dpapi(data, protect):
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(data, len(data))
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    target = Blob()
    crypt32 = ctypes.windll.crypt32
    call = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    # CRYPTPROTECT_UI_FORBIDDEN: nunca abrir diálogo do sistema.
    if not call(
        ctypes.byref(source), None, None, None, None, 0x01, ctypes.byref(target)
    ):
        raise OSError("DPAPI recusou o token salvo.")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.windll.kernel32.LocalFree(target.data)


def save(path, refresh_token):
    if (
        not isinstance(refresh_token, str)
        or not refresh_token
        or len(refresh_token) > 4096
    ):
        raise ValueError("Token inválido.")
    raw = refresh_token.encode()
    if sys.platform == "win32":
        body = {"v": VERSION, "dpapi": base64.b64encode(_dpapi(raw, True)).decode()}
    else:
        body = {"v": VERSION, "token": refresh_token}
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(body, handle)
    os.replace(temporary, path)
    if sys.platform != "win32":
        os.chmod(path, 0o600)


def load(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 16384:
        return None
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
        if body.get("v") != VERSION:
            return None
        if "dpapi" in body:
            if sys.platform != "win32":
                return None
            return _dpapi(base64.b64decode(body["dpapi"]), False).decode()
        token = body.get("token")
        return token if isinstance(token, str) and token else None
    except (OSError, ValueError, UnicodeError, AttributeError):
        return None


def clear(path):
    for candidate in (Path(path), Path(str(path) + ".tmp")):
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass
