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
    d = tempfile.mkdtemp()
    for f in ("build.py", "hist2526.py"):
        shutil.copy(f, d)
    cal = [{k: v for k, v in m.items() if k != "asistentes"} for m in partidos]
    rep = {m["id"]: m["asistentes"] for m in partidos}
    json.dump(cal, open(os.path.join(d, "calendario.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    json.dump(rep, open(os.path.join(d, "reparto.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    subprocess.run([sys.executable, "hist2526.py"], cwd=d,
                   capture_output=True, text=True, check=True)
    r = subprocess.run([sys.executable, "build.py"], cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip()[:400]
    return open(os.path.join(d, "index.html"), encoding="utf-8").read(), ""


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


if __name__ == "__main__":
    test_aviso_en_la_web()
    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s): " + ", ".join(FALLOS))
        sys.exit(1)
    print("todo en orden")
