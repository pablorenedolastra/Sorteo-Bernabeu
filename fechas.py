# -*- coding: utf-8 -*-
"""Fechas de la API a texto en español, en hora de Madrid.

Dos decisiones que parecen menores y no lo son:

  - La API da las horas en UTC. En temporada eso son dos horas de diferencia en
    verano y una en invierno, así que un 21:00 real llega como 19:00Z o 20:00Z
    según el mes. Se convierte con zoneinfo, de la librería estándar, para no
    añadir dependencias al proyecto.

  - Los nombres de días y meses van en tablas propias, NO con
    locale.setlocale(LC_TIME, "es_ES"). Ese locale no está instalado en el runner
    de Ubuntu de GitHub Actions: el script funcionaría en el Mac y fallaría solo en
    producción, que es la peor forma de fallar.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def a_madrid(utc_txt):
    """"2026-08-26T19:00:00Z" -> datetime en hora de Madrid. None si no se entiende."""
    if not utc_txt or not isinstance(utc_txt, str):
        return None
    try:
        d = datetime.fromisoformat(utc_txt.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(MADRID)


def fmt_fecha(d):
    """datetime -> "Mié 26 ago 2026", el formato que usa la web."""
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]} {d.year}"


def fmt_hora(d):
    """datetime -> "21:00"."""
    return f"{d.hour:02d}:{d.minute:02d}"


def fmt_sort(d):
    """datetime -> "2026-08-26", la clave con la que build.py ordena el calendario."""
    return d.strftime("%Y-%m-%d")
