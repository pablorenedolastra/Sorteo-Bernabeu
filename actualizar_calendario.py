# -*- coding: utf-8 -*-
"""Actualiza calendario.json con las fechas que publica football-data.org.

Lo lanza cada noche .github/workflows/actualizar-calendario.yml.

Este script NO puede alterar el reparto de entradas, y eso es deliberado: solo
escribe en calendario.json, que no contiene asistentes. Quién va a cada partido
vive en reparto.json, congelado, y lo genera sorteo.py cuando una persona lo
lanza a mano. La razón está explicada al final de sorteo.py.

Dos principios que gobiernan todo lo de abajo:

  1. Un fallo nunca debe empeorar la web. Ante cualquier respuesta que no se
     entienda del todo, el script aborta sin escribir: una fecha vieja es mejor
     que una inventada, y mucho mejor que un index.html roto.

  2. No se degrada un dato bueno. Un rango escrito a mano como "12/13 sep 2026"
     es información real; una fecha que la API marca como SCHEDULED es una
     estimación peor. Solo se escribe cuando la API la da por finalizada.

Uso:
    python3 actualizar_calendario.py --dry-run     # dice qué cambiaría, sin tocar nada
    python3 actualizar_calendario.py               # actualiza calendario.json
    python3 actualizar_calendario.py --descubrir-ids   # lista los api_team de la API
"""
import argparse, json, os, sys, urllib.error, urllib.request
from datetime import datetime

import fechas

BASE = "https://api.football-data.org/v4"
ID_MADRID = 86            # confirmado contra /v4/competitions/PD/teams (7 sep 2026)
TEMPORADA = 2026
CALENDARIO = "calendario.json"

SIN_RIVAL = "Rival por determinar"

# Estados en los que la fecha y la hora de la API son firmes. SCHEDULED queda fuera
# a propósito: ahí la API todavía da una estimación.
FIRMES = {"TIMED", "IN_PLAY", "PAUSED", "FINISHED", "AWARDED"}

# Estados que merecen un aviso visible en la web.
AVISOS = {"POSTPONED": "⚠️ Partido aplazado",
          "SUSPENDED": "⚠️ Partido suspendido",
          "CANCELLED": "⚠️ Partido cancelado"}

# Campos que solo cambia una persona. Si la actualización toca alguno, algo va mal
# y se aborta.
INTOCABLES = ("comp", "ronda", "nivel", "nota", "seats", "bloque", "api_team", "api_stage")

# Por debajo de esto, la respuesta de la API no es de fiar. El Madrid juega 38
# partidos de liga y 8 de fase liga, así que una respuesta sana trae 46 o más.
MIN_PARTIDOS = 30

# Margen para avisar de que una fecha SCHEDULED se ha ido del rango escrito a mano.
# Los rangos del calendario abarcan dos o tres días ("12/13 sep 2026"), así que tres
# días de tolerancia distinguen "la jornada se ha movido" de "aún no está fijada".
DIAS_MARGEN = 3


def nombre_rival(partido):
    """El nombre corto del rival: "Real Sociedad", no "Real Sociedad de Futbol"."""
    visitante = partido.get("awayTeam") or {}
    local = partido.get("homeTeam") or {}
    otro = visitante if local.get("id") == ID_MADRID else local
    return otro.get("shortName") or otro.get("name") or ""


def emparejar(cal, partidos):
    """{id nuestro: partido de la API}, solo partidos en el Bernabéu.

    Se empareja por id numérico de equipo y no por nombre: la API dice "Real
    Sociedad de Futbol" y "Club Atletico de Madrid" donde el calendario dice
    "Real Sociedad" y "Atlético de Madrid", y perseguir esa correspondencia
    normalizando cadenas es una fuente inagotable de bugs.

    Que el Madrid sea el local desambigua solo las dos vueltas de LaLiga y las
    idas y vueltas de las eliminatorias. Si un partido queda con más de un
    candidato, no se empareja: mejor no tocarlo que tocarlo mal.
    """
    en_casa = [p for p in partidos if (p.get("homeTeam") or {}).get("id") == ID_MADRID]

    por_rival, por_stage = {}, {}
    for p in en_casa:
        rid = (p.get("awayTeam") or {}).get("id")
        if rid is not None:
            por_rival.setdefault(rid, []).append(p)
        if p.get("stage"):
            por_stage.setdefault(p["stage"], []).append(p)

    out = {}
    for m in cal:
        if m.get("api_team") is not None:
            cands = por_rival.get(m["api_team"], [])
        elif m.get("api_stage"):
            cands = por_stage.get(m["api_stage"], [])
        else:
            cands = []          # Copa del Rey: no la cubre el plan gratuito
        if len(cands) == 1:
            out[m["id"]] = cands[0]
    return out
