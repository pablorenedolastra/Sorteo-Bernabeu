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


# ---------------------------------------------------------------- separación
def test_separacion():
    bloque("Separación de calendario y reparto")
    ref = json.load(open("tests/sorteo_referencia.json"))
    cal = json.load(open("calendario.json"))
    rep = json.load(open("reparto.json"))

    check("el calendario tiene los 29 partidos", len(cal) == 29, f"tiene {len(cal)}")
    check("el reparto tiene los 29 partidos", len(rep) == 29, f"tiene {len(rep)}")
    check("el calendario no lleva asistentes",
          all("asistentes" not in m for m in cal),
          "algún partido de calendario.json lleva asistentes: el cron podría tocar el reparto")

    # reconstruir el sorteo.json de siempre y comparar campo a campo
    recon = [dict(m, asistentes=rep[m["id"]]) for m in cal]
    recon.sort(key=lambda m: m["sort"])
    por_id = {m["id"]: m for m in recon}
    dif = []
    for m in ref:
        n = por_id.get(m["id"])
        if n is None:
            dif.append(f'{m["id"]}: no está en el calendario')
            continue
        for k, v in m.items():
            if n.get(k) != v:
                dif.append(f'{m["id"]}.{k}: {v!r} -> {n.get(k)!r}')
    detalle = "\n        ".join(dif[:10])
    if len(dif) > 10:
        detalle += f"\n        (y {len(dif) - 10} diferencia(s) más)"
    check("el reparto es idéntico al de antes del refactor", not dif, detalle)


if __name__ == "__main__":
    if not os.path.exists("calendario.json"):
        print("falta calendario.json: ejecuta python3 sorteo.py")
        sys.exit(1)
    test_separacion()
    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s): " + ", ".join(FALLOS))
        sys.exit(1)
    print("todo en orden")
