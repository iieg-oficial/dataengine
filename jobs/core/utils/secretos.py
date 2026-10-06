import os
from pathlib import Path


def leer_secreto(nombre: str) -> str | None:
    directo = os.getenv(nombre)
    if directo:
        return directo
    ruta = os.getenv(f'{nombre}_FILE')
    if not ruta:
        return None
    try:
        return Path(ruta).read_text(encoding='utf-8').strip() or None
    except OSError:
        return None
