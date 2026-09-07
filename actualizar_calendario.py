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


def en_rango(m, d):
    """¿La fecha d encaja con lo que hay escrito en el partido m?

    Las fechas del calendario son a veces rangos ("12/13 sep 2026", "27/28 abr o
    4/5 may 2027") que no se pueden parsear de forma fiable, pero cada partido
    lleva su clave `sort` con el día central. Comparar contra ella con unos días
    de margen basta para lo único que se quiere: distinguir "LaLiga ha movido la
    jornada" de "la fecha aún no está fijada".
    """
    try:
        ref = datetime.strptime(m["sort"], "%Y-%m-%d").date()
    except (ValueError, KeyError, TypeError):
        return True          # sin referencia fiable, no se avisa de nada
    return abs((d.date() - ref).days) <= DIAS_MARGEN


def aplicar(cal, emparejados):
    """Calendario actualizado, lista de cambios y lista de avisos.

    Función pura: no lee ni escribe ficheros, no toca la red. Todo lo que decide
    está en la tabla de precedencia del spec:

      fecha, hora, sort  -> la API, y solo si el estado es firme
      rival              -> la API, y solo si aún dice "Rival por determinar"
      estado, aviso      -> la API, siempre
      el resto           -> la persona; aquí no se tocan nunca
    """
    nuevo, cambios, avisos = [], [], []

    for m in cal:
        m = dict(m)
        p = emparejados.get(m["id"])
        if p is None:
            nuevo.append(m)
            continue

        estado_antes = m.get("estado")
        estado = p.get("status") or ""
        m["estado"] = estado

        # El rival, solo si todavía no se conoce. Se rellena la etiqueta y nada
        # más: cuando se conoce un rival su nivel real cambia, y renivelar el
        # bloque es una decisión humana en POST de sorteo.py, no de un script
        # de madrugada. Por eso `nivel` está en INTOCABLES.
        if m.get("rival") == SIN_RIVAL:
            r = nombre_rival(p)
            if r:
                cambios.append(f'{m["id"]}: rival por determinar -> {r}')
                m["rival"] = r

        d = fechas.a_madrid(p.get("utcDate"))
        if d and estado in FIRMES:
            f, h, s = fechas.fmt_fecha(d), fechas.fmt_hora(d), fechas.fmt_sort(d)
            # Dos cosas distintas que conviene no mezclar en el informe: que cambie
            # la fecha (se ve en la web) y que la API confirme una fecha que ya
            # estaba bien escrita (solo cambia el estado). Las dos son noticia,
            # pero decirlas igual haría que el mensaje del commit mintiera.
            if (f, h) != (m.get("fecha"), m.get("hora")):
                cambios.append(f'{m["id"]}: {m.get("fecha")} {m.get("hora")} -> {f} {h}')
                m["fecha"], m["hora"], m["sort"] = f, h, s
            elif estado != estado_antes:
                cambios.append(f'{m["id"]}: {f} {h} sigue igual, la API pasa de'
                               f' {estado_antes} a {estado}')
                m["sort"] = s
        elif d and estado == "SCHEDULED" and not en_rango(m, d):
            # No se sobreescribe (sería degradar un dato bueno con una estimación),
            # pero conviene enterarse: es la pista de que la jornada se ha movido.
            avisos.append(f'{m["id"]}: la API apunta al {d:%d/%m/%Y},'
                          f' fuera de "{m.get("fecha")}"')

        m["aviso"] = AVISOS.get(estado, "")
        nuevo.append(m)

    nuevo.sort(key=lambda m: m["sort"])
    return nuevo, cambios, avisos


def validar(viejo, nuevo):
    """Lista de problemas del calendario nuevo. Vacía si se puede escribir.

    Es la red de seguridad del script: la actualización solo debería mover fechas,
    horas, rivales por determinar y avisos. Si ha tocado cualquier otra cosa, algo
    ha ido mal y es preferible no escribir nada.
    """
    problemas = []
    vi = {m["id"]: m for m in viejo}
    ni = {m["id"]: m for m in nuevo}

    if len(nuevo) != len(viejo):
        problemas.append(f"el calendario pasa de {len(viejo)} a {len(nuevo)} partidos")
    if len(ni) != len(nuevo):
        problemas.append("hay ids repetidos en el calendario nuevo")

    for i in sorted(set(vi) - set(ni)):
        problemas.append(f"desaparece el partido {i}")
    for i in sorted(set(ni) - set(vi)):
        problemas.append(f"aparece un partido que no estaba: {i}")

    for i in sorted(set(vi) & set(ni)):
        for campo in INTOCABLES:
            if vi[i].get(campo) != ni[i].get(campo):
                problemas.append(f'{i}: {campo} cambia de {vi[i].get(campo)!r}'
                                 f' a {ni[i].get(campo)!r}')

    for bloque in ("LIGA", "EURO"):
        a = sum(m["seats"] for m in viejo if m.get("bloque") == bloque)
        b = sum(m["seats"] for m in nuevo if m.get("bloque") == bloque)
        if a != b:
            problemas.append(f"los asientos del bloque {bloque} pasan de {a} a {b}")

    return problemas
