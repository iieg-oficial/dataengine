from __future__ import annotations

from datetime import date
from statistics import median

FRECUENCIA_POR_DIAS: tuple[tuple[float, str], ...] = (
    (1.5, 'Diaria'),
    (10.0, 'Semanal'),
    (20.0, 'Quincenal'),
    (45.0, 'Mensual'),
    (75.0, 'Bimestral'),
    (105.0, 'Trimestral'),
    (150.0, 'Cuatrimestral'),
    (270.0, 'Semestral'),
    (550.0, 'Anual'),
    (900.0, 'Bianual'),
    (1400.0, 'Trienal'),
    (2200.0, 'Quinquenal'),
)

FRECUENCIA_MAS_LARGA = 'Decenal'


def fechas_de(periodicidad: dict) -> list[date]:
    fechas: list[date] = []
    for anio, meses in (periodicidad or {}).items():
        if not isinstance(meses, dict):
            continue
        for mes, dias in meses.items():
            for dia in (dias or [1]):
                try:
                    fechas.append(date(int(anio), int(mes), int(dia)))
                except (TypeError, ValueError):
                    continue
    return sorted(set(fechas))


def solo_anual(fechas: list[date]) -> bool:
    return all(f.month == 1 and f.day == 1 for f in fechas)


def fecha_sugerida(fechas: list[date]) -> str | None:
    if not fechas:
        return None
    ultima = fechas[-1]
    return str(ultima.year) if solo_anual(fechas) else ultima.isoformat()


def frecuencia_sugerida(fechas: list[date]) -> str | None:
    if len(fechas) < 2:
        return None
    brechas = [
        (b - a).days
        for a, b in zip(fechas, fechas[1:])
        if (b - a).days > 0
    ]
    if not brechas:
        return None
    tipica = median(brechas)
    for tope, etiqueta in FRECUENCIA_POR_DIAS:
        if tipica <= tope:
            return etiqueta
    return FRECUENCIA_MAS_LARGA


def sugerencias_de(periodicidad: dict) -> tuple[str | None, str | None]:
    fechas = fechas_de(periodicidad)
    return fecha_sugerida(fechas), frecuencia_sugerida(fechas)
