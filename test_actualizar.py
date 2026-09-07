# -*- coding: utf-8 -*-
"""Tests del proyecto. Sin dependencias: python3 test_actualizar.py"""
import json, sys, os

FALLOS = []

def check(nombre, cond, detalle=""):
    if cond:
        print(f"  ok    {nombre}")
    else:
        print(f"  FALLO {nombre}" + (f"\n        {detalle}" if detalle else ""))
        FALLOS.append(nombre)

def bloque(titulo):
    print(f"\n{titulo}")


# --------------------------------------------------------------- avisos en la web
def _build_en_tmp(partidos):
    """Ejecuta build.py en un directorio aparte y devuelve el index.html generado.

    build.py NO se puede importar: al cargarse lee los JSON y reescribe
    index.html, así que un `import build` en un test destrozaría la web del
    repo. Se ejecuta como proceso en un tmpdir con los datos que interesan.
    """
    import shutil, subprocess, tempfile
    with tempfile.TemporaryDirectory() as d:
        for script in ("build.py", "hist2526.py"):
            shutil.copy(script, d)
        cal = [{k: v for k, v in m.items() if k != "asistentes"} for m in partidos]
        rep = {m["id"]: m["asistentes"] for m in partidos}
        for nombre, datos in (("calendario.json", cal), ("reparto.json", rep)):
            with open(os.path.join(d, nombre), "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False)
        # Los dos scripts se tratan igual: si cualquiera falla se devuelve su stderr
        # para que el test lo reporte con check(), en vez de reventar la ejecución
        # entera con un traceback y llevarse por delante los demás bloques.
        for script in ("hist2526.py", "build.py"):
            r = subprocess.run([sys.executable, script], cwd=d,
                               capture_output=True, text=True)
            if r.returncode != 0:
                return None, f"{script}: {r.stderr.strip()[:400]}"
        with open(os.path.join(d, "index.html"), encoding="utf-8") as f:
            return f.read(), ""


def _partido_de_prueba(**extra):
    base = {
        "id": "L1", "comp": "LIGA", "ronda": "J1", "fecha": "Mié 26 ago 2026",
        "sort": "2026-08-26", "rival": "Real Sociedad", "nivel": 2, "hora": "21:00",
        "nota": "Estreno en casa", "seats": 2, "bloque": "LIGA",
        "estado": "TIMED", "aviso": "", "api_team": 92, "api_stage": None,
        "asistentes": ["Pablo", "Víctor"],
    }
    base.update(extra)
    return base


# ------------------------------------------------------------------- fechas.py
def test_fechas():
    bloque("Conversión de fechas y formato español")
    import fechas

    # Verano: Madrid va 2 horas por delante de UTC
    d = fechas.a_madrid("2026-08-26T19:00:00Z")
    check("verano: 19:00Z son las 21:00 en Madrid", fechas.fmt_hora(d) == "21:00",
          f"da {fechas.fmt_hora(d)}")
    check("verano: la fecha se formatea en español", fechas.fmt_fecha(d) == "Mié 26 ago 2026",
          f"da {fechas.fmt_fecha(d)}")
    check("verano: la clave de orden es ISO", fechas.fmt_sort(d) == "2026-08-26",
          f"da {fechas.fmt_sort(d)}")

    # Invierno: Madrid va 1 hora por delante
    d = fechas.a_madrid("2027-01-19T20:00:00Z")
    check("invierno: 20:00Z son las 21:00 en Madrid", fechas.fmt_hora(d) == "21:00",
          f"da {fechas.fmt_hora(d)}")
    check("invierno: la fecha se formatea en español", fechas.fmt_fecha(d) == "Mar 19 ene 2027",
          f"da {fechas.fmt_fecha(d)}")

    # Un partido a medianoche UTC cae al día siguiente en Madrid
    d = fechas.a_madrid("2027-03-13T23:30:00Z")
    check("23:30Z de un 13 de marzo es el 14 en Madrid",
          fechas.fmt_fecha(d) == "Dom 14 mar 2027", f"da {fechas.fmt_fecha(d)}")

    # Entradas inválidas devuelven None en vez de reventar
    for malo in (None, "", "no soy una fecha", "2026-13-45T99:00:00Z"):
        check(f"a_madrid({malo!r}) devuelve None", fechas.a_madrid(malo) is None)

    # Los doce meses y los siete días, para que no haya un mes escrito a medias
    meses = [fechas.fmt_fecha(fechas.a_madrid(f"2026-{m:02d}-15T12:00:00Z")).split()[2]
             for m in range(1, 13)]
    check("los doce meses tienen abreviatura",
          meses == ["ene", "feb", "mar", "abr", "may", "jun",
                    "jul", "ago", "sep", "oct", "nov", "dic"], f"da {meses}")
    dias = [fechas.fmt_fecha(fechas.a_madrid(f"2026-06-{d:02d}T12:00:00Z")).split()[0]
            for d in range(1, 8)]
    check("los siete días tienen abreviatura",
          dias == ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"], f"da {dias}")


def test_aviso_en_la_web():
    bloque("La web muestra los avisos de la API")

    html, err = _build_en_tmp([_partido_de_prueba(aviso="⚠️ Partido aplazado")])
    check("build.py genera la web con un aviso", html is not None, err)
    if html is None:
        return
    check("el aviso aparece en el HTML", "Partido aplazado" in html)
    check("la nota sigue apareciendo", "Estreno en casa" in html)
    check("el aviso lleva su propia clase", 'class="nota aviso"' in html)

    limpio, err = _build_en_tmp([_partido_de_prueba()])
    check("sin aviso no se pinta el div",
          limpio is not None and 'class="nota aviso"' not in limpio, err)

    # Los partidos de 2025/26 (hist2526.json) no tienen el campo `aviso`. build.py
    # los pinta en la misma función, así que tiene que aguantarlo sin petar. Si esto
    # falla, es que se ha usado m["aviso"] en vez de m.get("aviso").
    sin_campo = _partido_de_prueba()
    del sin_campo["aviso"]
    html2, err2 = _build_en_tmp([sin_campo])
    check("un partido sin el campo aviso no rompe el render", html2 is not None, err2)


# -------------------------------------------------------------- emparejamiento
def _cal_prueba():
    """Cuatro partidos del calendario real, con los api_team del fixture."""
    return [
        {"id": "L1", "comp": "LIGA", "ronda": "J1", "fecha": "Mié 26 ago 2026",
         "sort": "2026-08-26", "rival": "Real Sociedad", "nivel": 2, "hora": "21:00",
         "nota": "Estreno en casa", "seats": 2, "bloque": "LIGA",
         "estado": "SCHEDULED", "aviso": "", "api_team": 92, "api_stage": None},
        {"id": "L5", "comp": "LIGA", "ronda": "J5", "fecha": "12/13 sep 2026",
         "sort": "2026-09-12", "rival": "Rayo Vallecano", "nivel": 3, "hora": "TBD",
         "nota": "", "seats": 2, "bloque": "LIGA",
         "estado": "SCHEDULED", "aviso": "", "api_team": 87, "api_stage": None},
        {"id": "L16", "comp": "LIGA", "ronda": "J16", "fecha": "12/13 dic 2026",
         "sort": "2026-12-12", "rival": "CA Osasuna", "nivel": 3, "hora": "TBD",
         "nota": "", "seats": 2, "bloque": "LIGA",
         "estado": "SCHEDULED", "aviso": "", "api_team": 79, "api_stage": None},
        {"id": "C6", "comp": "CHAMPIONS", "ronda": "Octavos (vuelta)",
         "fecha": "16/17 mar 2027", "sort": "2027-03-16", "rival": "Rival por determinar",
         "nivel": 2, "hora": "21:00", "nota": "Teórico", "seats": 2, "bloque": "EURO",
         "estado": "SCHEDULED", "aviso": "", "api_team": None, "api_stage": "LAST_16"},
        {"id": "K1", "comp": "COPA", "ronda": "Cuartos de final", "fecha": "Mié 13 ene 2027",
         "sort": "2027-01-13", "rival": "Rival por determinar", "nivel": 2, "hora": "TBD",
         "nota": "Teórico · solo si se juega en el Bernabéu", "seats": 2, "bloque": "EURO",
         "estado": "SCHEDULED", "aviso": "", "api_team": None, "api_stage": None},
    ]


def _partidos_fixture():
    return json.load(open("tests/respuesta_api.json"))["matches"]


def test_emparejar():
    bloque("Emparejamiento API ↔ calendario")
    import actualizar_calendario as ac
    par = ac.emparejar(_cal_prueba(), _partidos_fixture())

    check("empareja por id de equipo, no por nombre", par.get("L1", {}).get("id") == 500001,
          f'L1 -> {par.get("L1", {}).get("id")}')
    check("empareja el Rayo", par.get("L5", {}).get("id") == 500002)
    check("empareja una eliminatoria por stage", par.get("C6", {}).get("id") == 500007,
          f'C6 -> {par.get("C6", {}).get("id")}')
    check("descarta la ida a domicilio de la eliminatoria",
          par.get("C6", {}).get("homeTeam", {}).get("id") == ac.ID_MADRID)
    check("la Copa del Rey no se empareja (no la cubre el plan gratuito)",
          "K1" not in par, f'K1 -> {par.get("K1")}')
    check("un partido sin correspondencia en la API no se empareja",
          "L21" not in par)


if __name__ == "__main__":
    test_fechas()
    test_aviso_en_la_web()
    test_emparejar()
    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s): " + ", ".join(FALLOS))
        sys.exit(1)
    print("todo en orden")
