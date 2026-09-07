# Actualización diaria del calendario — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que las fechas, horas y rivales de los partidos en la web se actualicen solos cada noche desde football-data.org, sin que ningún proceso automático pueda alterar el reparto de entradas.

**Architecture:** Se separa lo que hoy vive junto en la tabla `M` de `sorteo.py`: el calendario pasa a `calendario.json` (mutable, lo escribe el cron) y el reparto a `reparto.json` (congelado, en git). `build.py` los vuelve a juntar para generar `index.html`. Un workflow de GitHub Actions ejecuta la actualización de madrugada y commitea solo si algo cambió.

**Tech Stack:** Python 3 y solo librería estándar (`urllib`, `json`, `zoneinfo`, `argparse`) — el proyecto no tiene dependencias externas y no se le añaden. GitHub Actions. GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-07-actualizacion-diaria-calendario-design.md`

---

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `calendario.json` | **Nuevo, en git.** Los 29 partidos: fecha, hora, rival, estado, aviso (mutables) + nivel, nota, seats, ronda, bloque, api_team, api_stage (estables). Sin asistentes. |
| `reparto.json` | **Nuevo, en git.** Mapa `id → asistentes`, con `POST` aplicado. La salida congelada del sorteo. |
| `fechas.py` | **Nuevo.** Convertir `utcDate` a hora de Madrid y formatear en español. Puro, sin I/O. |
| `actualizar_calendario.py` | **Nuevo.** Cliente de la API, emparejamiento, precedencia, validación y CLI. |
| `test_actualizar.py` | **Nuevo.** Tests de `fechas.py` y `actualizar_calendario.py`, sin dependencias. |
| `tests/respuesta_api.json` | **Nuevo.** Respuesta de la API guardada, para probar el parseo sin red. |
| `tests/index_referencia.html` | **Nuevo, temporal.** Copia de `index.html` antes del refactor, para probar que la separación no cambia la web. Se borra en la tarea 3. |
| `.github/workflows/actualizar-calendario.yml` | **Nuevo.** El cron. |
| `sorteo.py` | **Modificar el final.** Escribe `reparto.json` y `calendario.json` en vez de `sorteo.json`. Su lógica no se toca. |
| `build.py` | **Modificar** la carga de datos (línea 194) y el render de la nota (línea 56). |
| `.gitignore` | **Modificar.** Quitar `sorteo.json`. |
| `README.md` | **Modificar.** Documentar el nuevo flujo. |

La lógica de `actualizar_calendario.py` se escribe como funciones puras (`emparejar`, `aplicar`, `validar`) con una capa fina de I/O encima. Es lo que permite testearla sin red y lo que mantiene el fichero legible.

---

## Task 1: Congelar el reparto

Lo primero y lo más delicado: separar los datos sin que el reparto cambie. El test es de regresión pura — los dos ficheros nuevos tienen que reconstruir exactamente el `sorteo.json` que hay hoy en disco.

**Files:**
- Modify: `sorteo.py` (últimas líneas, el `json.dump`)
- Modify: `.gitignore`
- Create: `reparto.json`, `calendario.json` (generados)
- Test: `test_actualizar.py`

- [ ] **Step 1: Guardar el `sorteo.json` actual como referencia**

Se necesita antes de tocar nada, porque `sorteo.py` lo va a dejar de escribir.

```bash
cd "/Users/parenedo/Claude PRL/Sorteo-Bernabeu"
mkdir -p tests
python3 sorteo.py >/dev/null && cp sorteo.json tests/sorteo_referencia.json
python3 -c "import json; print(len(json.load(open('tests/sorteo_referencia.json'))), 'partidos guardados')"
```

Esperado: `29 partidos guardados`

- [ ] **Step 2: Escribir el test de regresión (falla)**

Crear `test_actualizar.py`:

```python
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
    check("el reparto es idéntico al de antes del refactor", not dif, "\n        ".join(dif[:10]))


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
```

- [ ] **Step 3: Ejecutar el test para verificar que falla**

Run: `python3 test_actualizar.py`

Esperado: `falta calendario.json: ejecuta python3 sorteo.py` y código de salida 1.

- [ ] **Step 4: Cambiar la salida de `sorteo.py`**

Sustituir las últimas líneas de `sorteo.py` (el `json.dump` que escribe `sorteo.json`) por:

```python
# ---- salida ----
# El calendario y el reparto se guardan por separado a propósito. El calendario lo
# actualiza actualizar_calendario.py cada noche; el reparto es la salida de este
# sorteo, con POST ya aplicado, y no lo vuelve a tocar nada automático.
#
# Esto no es una manía de orden. Las fechas son una ENTRADA de este script: M.sort
# ordena por fecha y las reglas 3 y 4 de score() se evalúan sobre ese orden. Si un
# cron cambiara una fecha y volviera a lanzar sorteo.py, el reparto podría salir
# distinto: otro Derbi, otro Clásico, otras parejas. Por eso el fichero que toca el
# cron no contiene asistentes: no tiene forma de alterar el reparto.
json.dump({m[0]: assign[m[0]] for m in M},
          open("reparto.json", "w"), ensure_ascii=False, indent=1)
print("\nreparto.json escrito")

# El calendario solo se crea si no existe. Si ya está, lleva encima el trabajo del
# cron (fechas confirmadas) y los api_team rellenados a mano, y machacarlo por
# relanzar el sorteo sería una pérdida silenciosa. Para rehacerlo, bórralo antes.
if os.path.exists("calendario.json"):
    print("calendario.json ya existe: no se toca."
          " Bórralo si de verdad quieres regenerarlo desde cero.")
else:
    json.dump([dict(id=m[0], comp=m[1], ronda=m[2], fecha=m[3], sort=m[4], rival=m[5],
                    nivel=m[6], hora=m[7], nota=m[8], seats=m[9], bloque=m[10],
                    estado="SCHEDULED", aviso="", api_team=None, api_stage=None)
               for m in M], open("calendario.json", "w"), ensure_ascii=False, indent=1)
    print("calendario.json creado. Rellena api_team y api_stage con:"
          "\n  python3 actualizar_calendario.py --descubrir-ids")
```

Y añadir `os` al import de la primera línea:

```python
import random, json, itertools, os
```

- [ ] **Step 5: Generar los ficheros y ejecutar el test**

```bash
python3 sorteo.py | tail -5
python3 test_actualizar.py
```

Esperado: `reparto.json escrito`, `calendario.json creado`, y el test en verde con `todo en orden`.

Si "el reparto es idéntico al de antes del refactor" falla, **para**: significa que el refactor ha movido el sorteo y hay que averiguar por qué antes de seguir.

- [ ] **Step 6: Comprobar la salvaguarda de `calendario.json`**

```bash
python3 sorteo.py | grep calendario
```

Esperado: `calendario.json ya existe: no se toca. Bórralo si de verdad quieres regenerarlo desde cero.`

- [ ] **Step 7: Quitar `sorteo.json` del `.gitignore`**

`reparto.json` y `calendario.json` van a git: dejan de ser regenerables y pasan a ser la fuente de verdad. `sorteo.json` ya no lo escribe nadie.

```bash
python3 - <<'PY'
import io
p = ".gitignore"
s = io.open(p, encoding="utf-8").read()
s = s.replace("sorteo.json\n", "")
if "tests/sorteo_referencia.json" not in s:
    s = "# referencia temporal del refactor (tarea 3 la borra)\ntests/sorteo_referencia.json\n" + s
io.open(p, "w", encoding="utf-8").write(s)
PY
cat .gitignore
rm -f sorteo.json
```

Esperado: el `.gitignore` ya no menciona `sorteo.json` y sí `tests/sorteo_referencia.json`.

- [ ] **Step 8: Commit**

```bash
git add sorteo.py .gitignore calendario.json reparto.json test_actualizar.py
git commit -m "$(cat <<'MSG'
Separa el calendario del reparto

Las fechas son una entrada de sorteo.py: M.sort ordena por fecha y las reglas
3 y 4 de score() se evaluan sobre ese orden. Un cron que cambiara una fecha y
relanzara el sorteo podria devolver otro reparto.

Asi que el calendario (mutable) y el reparto (congelado) se separan en dos
ficheros, y el que va a tocar el cron no contiene asistentes. El test de
regresion comprueba que la separacion no ha movido el sorteo.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
```

---

## Task 2: `build.py` lee los dos ficheros

El test aquí es exigente a propósito: el `index.html` generado tiene que salir **idéntico byte a byte** al que hay commiteado. Si el refactor no cambia la web, no cambia nada.

**Files:**
- Modify: `build.py:194` (carga de datos)
- Create: `tests/index_referencia.html`
- Test: `test_actualizar.py`

- [ ] **Step 1: Guardar el `index.html` actual como referencia**

```bash
cp index.html tests/index_referencia.html
python3 -c "print(open('tests/index_referencia.html').read().__len__(), 'bytes de referencia')"
```

Esperado: `55708 bytes de referencia` (o el tamaño que tenga el fichero commiteado).

- [ ] **Step 2: Escribir el test (falla)**

Añadir a `test_actualizar.py`, antes del `if __name__`:

```python
# ------------------------------------------------------------------- build.py
def test_build_no_cambia_la_web():
    bloque("build.py genera la misma web que antes del refactor")
    import subprocess
    r = subprocess.run([sys.executable, "build.py"], capture_output=True, text=True)
    check("build.py termina sin error", r.returncode == 0, r.stderr.strip()[:400])
    if r.returncode != 0:
        return
    nuevo = open("index.html", encoding="utf-8").read()
    viejo = open("tests/index_referencia.html", encoding="utf-8").read()
    if nuevo == viejo:
        check("index.html es idéntico al de referencia", True)
        return
    # localizar la primera línea que difiere, para que el fallo sea útil
    a, b = viejo.splitlines(), nuevo.splitlines()
    det = f"referencia {len(a)} líneas, generado {len(b)}"
    for i, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            det = f"primera diferencia en la línea {i}:\n        - {x[:150]}\n        + {y[:150]}"
            break
    check("index.html es idéntico al de referencia", False, det)
```

Y registrarlo en el `main`, sustituyendo el bloque `if __name__` por:

```python
if __name__ == "__main__":
    if not os.path.exists("calendario.json"):
        print("falta calendario.json: ejecuta python3 sorteo.py")
        sys.exit(1)
    test_separacion()
    test_build_no_cambia_la_web()
    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s): " + ", ".join(FALLOS))
        sys.exit(1)
    print("todo en orden")
```

- [ ] **Step 3: Ejecutar el test para verificar que falla**

Run: `python3 test_actualizar.py`

Esperado: `FALLO build.py termina sin error` con un `FileNotFoundError: 'sorteo.json'` en el detalle — `build.py` sigue buscando el fichero que ya no existe.

- [ ] **Step 4: Cambiar la carga de datos en `build.py`**

Sustituir la línea 194, `D27 = json.load(open("sorteo.json"))`, por:

```python
# El calendario (mutable, lo actualiza el cron cada noche) y el reparto (congelado,
# la salida del sorteo) viven en ficheros separados. Aquí se vuelven a juntar para
# pintar la web. Ver la nota del final de sorteo.py sobre por qué están separados.
CAL = json.load(open("calendario.json"))
REP = json.load(open("reparto.json"))
huerfanos = [m["id"] for m in CAL if m["id"] not in REP]
assert not huerfanos, f"partidos del calendario que no están en reparto.json: {huerfanos}"
D27 = sorted((dict(m, asistentes=REP[m["id"]]) for m in CAL), key=lambda m: m["sort"])
```

- [ ] **Step 5: Ejecutar el test para verificar que pasa**

Run: `python3 test_actualizar.py`

Esperado: `ok    index.html es idéntico al de referencia` y `todo en orden`.

Si sale una diferencia, el refactor ha cambiado la web y hay que entender la línea que el test señala antes de continuar.

- [ ] **Step 6: Comprobar que el assert de huérfanos salta**

```bash
python3 - <<'PY'
import json, subprocess, sys, shutil
shutil.copy("reparto.json", "/tmp/reparto.bak")
rep = json.load(open("reparto.json"))
rep.pop("L1")
json.dump(rep, open("reparto.json", "w"), ensure_ascii=False, indent=1)
r = subprocess.run([sys.executable, "build.py"], capture_output=True, text=True)
shutil.copy("/tmp/reparto.bak", "reparto.json")
ok = r.returncode != 0 and "L1" in r.stderr
print("ok: build.py aborta si falta un partido en el reparto" if ok
      else f"MAL: no aborto como debia\n{r.stderr[-300:]}")
PY
python3 build.py >/dev/null && echo "index.html regenerado"
```

Esperado: `ok: build.py aborta si falta un partido en el reparto`, y luego `index.html regenerado`.

- [ ] **Step 7: Commit**

```bash
git add build.py test_actualizar.py tests/index_referencia.html
git commit -m "$(cat <<'MSG'
build.py cruza calendario.json y reparto.json

El test compara el index.html generado con el que habia commiteado, byte a
byte: el refactor no debe cambiar una sola linea de la web.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
```

---

## Task 3: Mostrar avisos de partidos aplazados en la web

Un partido aplazado es justo lo que quieres ver al abrir la página. El texto lo escribe la API en el campo `aviso`, separado de `nota` para que no haya pelea por la propiedad de ese texto.

**Files:**
- Modify: `build.py:56` (render de la nota) y el bloque de variables CSS (líneas 205-217)
- Delete: `tests/index_referencia.html`, `tests/sorteo_referencia.json`
- Test: `test_actualizar.py`

- [ ] **Step 1: Escribir el test (falla)**

Añadir a `test_actualizar.py`, antes del `if __name__`:

```python
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
```

Registrarlo en el `main`, tras `test_build_no_cambia_la_web()`:

```python
    test_aviso_en_la_web()
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `python3 test_actualizar.py`

Esperado: `FALLO el aviso aparece en el HTML` y `FALLO el aviso lleva su propia clase`.

- [ ] **Step 3: Renderizar el aviso**

En `build.py`, sustituir la línea 56:

```python
        nota = f'<div class="nota">{esc(m["nota"])}</div>' if m["nota"] else ""
```

por:

```python
        # El aviso lo escribe la API (aplazado, suspendido, cancelado) y va primero,
        # porque es lo que cambia el plan. La nota es texto propio y se queda debajo.
        nota = ""
        if m.get("aviso"):
            nota += f'<div class="nota aviso">{esc(m["aviso"])}</div>'
        if m["nota"]:
            nota += f'<div class="nota">{esc(m["nota"])}</div>'
```

- [ ] **Step 4: Añadir el color del aviso a los tres temas**

`build.py` define las variables CSS tres veces (claro, oscuro por `prefers-color-scheme` y oscuro por `data-theme`). Hay que añadir `--warn` en las tres para que el aviso se lea en cualquiera:

```bash
python3 - <<'PY'
import io
p = "build.py"
s = io.open(p, encoding="utf-8").read()
claro = "  --ink:#0b0b0b;--ink2:#52514e;--ink3:#83817a;"
oscuro = "  --ink:#fff;--ink2:#c3c2b7;--ink3:#8f8e85;"
assert s.count(claro) == 1, s.count(claro)
assert s.count(oscuro) == 2, s.count(oscuro)
s = s.replace(claro, claro + "--warn:#a04510;")
s = s.replace(oscuro, oscuro + "--warn:#f0a070;")
# la regla del aviso, junto a la de .nota
nota = ".nota{{font-weight:400;color:var(--ink3);font-size:12px;margin-top:3px;max-width:34ch}}"
assert nota in s
s = s.replace(nota, nota + "\n.nota.aviso{{color:var(--warn);font-weight:600}}")
io.open(p, "w", encoding="utf-8").write(s)
print("build.py: --warn y .nota.aviso añadidos")
PY
```

Esperado: `build.py: --warn y .nota.aviso añadidos`

- [ ] **Step 5: Ejecutar el test para verificar que pasa**

Run: `python3 test_actualizar.py`

Esperado: los cinco checks del bloque de avisos en verde.

Nota: `index.html es idéntico al de referencia` **sigue pasando**, porque ningún partido tiene `aviso` todavía. Es la comprobación de que el cambio es inerte hasta que la API diga algo.

- [ ] **Step 6: Verificar el aviso a ojo**

El test ya comprueba el HTML generado. Para verlo con los ojos, sin tocar el
repo:

```bash
python3 - <<'PY'
import json, os, shutil, subprocess, sys, tempfile
d = tempfile.mkdtemp()
for f in ("build.py", "hist2526.py", "reparto.json"):
    shutil.copy(f, d)
cal = json.load(open("calendario.json", encoding="utf-8"))
cal[0]["aviso"] = "⚠️ Partido aplazado"
json.dump(cal, open(os.path.join(d, "calendario.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
subprocess.run([sys.executable, "hist2526.py"], cwd=d, check=True, capture_output=True)
subprocess.run([sys.executable, "build.py"], cwd=d, check=True, capture_output=True)
print("abre:", os.path.join(d, "index.html"))
PY
```

Esperado: la ruta de un `index.html` en un temporal. Abrirlo y ver el aviso en
naranja sobre la primera fila. El repo no se ha tocado.

- [ ] **Step 7: Retirar los ficheros de referencia del refactor**

Ya han hecho su trabajo: han demostrado que separar los datos no cambió la web. Mantenerlos convertiría cualquier cambio futuro de diseño en un fallo de test.

```bash
git rm -q --cached tests/index_referencia.html
rm -f tests/index_referencia.html tests/sorteo_referencia.json
python3 - <<'PY'
import io
p = ".gitignore"
s = io.open(p, encoding="utf-8").read()
s = s.replace("# referencia temporal del refactor (tarea 3 la borra)\ntests/sorteo_referencia.json\n", "")
io.open(p, "w", encoding="utf-8").write(s)
PY
```

Y quitar de `test_actualizar.py` las funciones `test_separacion` y `test_build_no_cambia_la_web` junto con sus dos llamadas en el `main`, dejando el `main` así:

```python
if __name__ == "__main__":
    test_aviso_en_la_web()
    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s): " + ", ".join(FALLOS))
        sys.exit(1)
    print("todo en orden")
```

- [ ] **Step 8: Ejecutar el test y commitear**

```bash
python3 test_actualizar.py
git add -A build.py test_actualizar.py .gitignore tests
git commit -m "$(cat <<'MSG'
La web muestra los avisos de partido aplazado

El aviso lo escribe la API en su propio campo, separado de nota, para que no
haya dos duenos del mismo texto. Se retiran los ficheros de referencia del
refactor: ya han demostrado que separar los datos no cambio la web.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
```

---

## Task 4: `fechas.py` — hora de Madrid y formato español

Dos cosas pequeñas que son la causa habitual de que estos scripts fallen solo en producción: la zona horaria y el locale.

**Files:**
- Create: `fechas.py`
- Test: `test_actualizar.py`

- [ ] **Step 1: Escribir los tests (fallan)**

Añadir a `test_actualizar.py`, antes del `if __name__`:

```python
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
```

Registrarlo en el `main`, antes de `test_aviso_en_la_web()`:

```python
    test_fechas()
```

- [ ] **Step 2: Ejecutar los tests para verificar que fallan**

Run: `python3 test_actualizar.py`

Esperado: `ModuleNotFoundError: No module named 'fechas'`.

- [ ] **Step 3: Escribir `fechas.py`**

```python
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
```

- [ ] **Step 4: Ejecutar los tests para verificar que pasan**

Run: `python3 test_actualizar.py`

Esperado: los catorce checks del bloque de fechas en verde.

- [ ] **Step 5: Commit**

```bash
git add fechas.py test_actualizar.py
git commit -m "$(cat <<'MSG'
fechas.py: hora de Madrid y formato espanol

Los nombres de dias y meses van en tablas propias, no con locale es_ES: ese
locale no existe en el runner de Ubuntu y el script funcionaria en el Mac
para fallar solo en produccion.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
```

---

## Task 5: Emparejar los partidos de la API con los nuestros

Por id numérico de equipo, nunca por nombre. La API dice "Real Sociedad de Fútbol" y "Club Atlético de Madrid" donde el proyecto dice "Real Sociedad" y "Atlético de Madrid".

**Files:**
- Create: `actualizar_calendario.py`
- Create: `tests/respuesta_api.json`
- Test: `test_actualizar.py`

- [ ] **Step 1: Crear el fixture de respuesta de la API**

Respuesta sintética construida con el esquema documentado del recurso `match`.
Los ids son inventados y controlados (`500001`, `500002`…) precisamente para que
los tests puedan afirmar cosas concretas sobre ellos. **Este fichero no se
sustituye nunca por datos reales**: en la tarea 10 se captura una respuesta de
verdad en un fichero aparte, para comprobar que la forma que aquí se supone es la
que la API manda de verdad.

Crear `tests/respuesta_api.json`:

```json
{
  "filters": {"season": "2026"},
  "resultSet": {"count": 8},
  "matches": [
    {
      "id": 500001,
      "utcDate": "2026-08-26T19:00:00Z",
      "status": "TIMED",
      "matchday": 1,
      "stage": "REGULAR_SEASON",
      "competition": {"id": 2014, "code": "PD", "name": "Primera Division"},
      "homeTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "Real Madrid"},
      "awayTeam": {"id": 92, "name": "Real Sociedad de Futbol", "shortName": "Real Sociedad"}
    },
    {
      "id": 500002,
      "utcDate": "2026-09-12T00:00:00Z",
      "status": "SCHEDULED",
      "matchday": 5,
      "stage": "REGULAR_SEASON",
      "competition": {"id": 2014, "code": "PD", "name": "Primera Division"},
      "homeTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "Real Madrid"},
      "awayTeam": {"id": 87, "name": "Rayo Vallecano de Madrid", "shortName": "Rayo Vallecano"}
    },
    {
      "id": 500003,
      "utcDate": "2026-10-10T00:00:00Z",
      "status": "SCHEDULED",
      "matchday": 8,
      "stage": "REGULAR_SEASON",
      "competition": {"id": 2014, "code": "PD", "name": "Primera Division"},
      "homeTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "Real Madrid"},
      "awayTeam": {"id": 94, "name": "Villarreal CF", "shortName": "Villarreal"}
    },
    {
      "id": 500004,
      "utcDate": "2026-12-12T20:00:00Z",
      "status": "POSTPONED",
      "matchday": 16,
      "stage": "REGULAR_SEASON",
      "competition": {"id": 2014, "code": "PD", "name": "Primera Division"},
      "homeTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "Real Madrid"},
      "awayTeam": {"id": 79, "name": "CA Osasuna", "shortName": "Osasuna"}
    },
    {
      "id": 500005,
      "utcDate": "2026-09-08T19:00:00Z",
      "status": "TIMED",
      "matchday": 1,
      "stage": "LEAGUE_STAGE",
      "competition": {"id": 2001, "code": "CL", "name": "UEFA Champions League"},
      "homeTeam": {"id": 108, "name": "FC Internazionale Milano", "shortName": "Inter"},
      "awayTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "Real Madrid"}
    },
    {
      "id": 500006,
      "utcDate": "2026-10-21T19:00:00Z",
      "status": "TIMED",
      "matchday": 3,
      "stage": "LEAGUE_STAGE",
      "competition": {"id": 2001, "code": "CL", "name": "UEFA Champions League"},
      "homeTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "Real Madrid"},
      "awayTeam": {"id": 721, "name": "RB Leipzig", "shortName": "RB Leipzig"}
    },
    {
      "id": 500007,
      "utcDate": "2027-03-16T20:00:00Z",
      "status": "TIMED",
      "stage": "LAST_16",
      "competition": {"id": 2001, "code": "CL", "name": "UEFA Champions League"},
      "homeTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "Real Madrid"},
      "awayTeam": {"id": 5, "name": "FC Bayern Munchen", "shortName": "Bayern"}
    },
    {
      "id": 500008,
      "utcDate": "2027-03-09T20:00:00Z",
      "status": "TIMED",
      "stage": "LAST_16",
      "competition": {"id": 2001, "code": "CL", "name": "UEFA Champions League"},
      "homeTeam": {"id": 5, "name": "FC Bayern Munchen", "shortName": "Bayern"},
      "awayTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "Real Madrid"}
    }
  ]
}
```

Los partidos 500005 y 500008 son a domicilio a propósito: el emparejamiento tiene que descartarlos.

- [ ] **Step 2: Escribir los tests de emparejamiento (fallan)**

Añadir a `test_actualizar.py`, antes del `if __name__`:

```python
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
```

Registrarlo en el `main`, tras `test_fechas()`:

```python
    test_emparejar()
```

- [ ] **Step 3: Ejecutar los tests para verificar que fallan**

Run: `python3 test_actualizar.py`

Esperado: `ModuleNotFoundError: No module named 'actualizar_calendario'`.

- [ ] **Step 4: Escribir la primera parte de `actualizar_calendario.py`**

```python
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
ID_MADRID = 86            # se confirma con --descubrir-ids antes del primer uso real
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
```

- [ ] **Step 5: Ejecutar los tests para verificar que pasan**

Run: `python3 test_actualizar.py`

Esperado: los seis checks del bloque de emparejamiento en verde.

- [ ] **Step 6: Commit**

```bash
git add actualizar_calendario.py test_actualizar.py tests/respuesta_api.json
git commit -m "$(cat <<'MSG'
Empareja los partidos de la API por id de equipo

Por id numerico y nunca por nombre: la API dice "Real Sociedad de Futbol"
donde el calendario dice "Real Sociedad". Si un partido queda con mas de un
candidato no se empareja: mejor no tocarlo que tocarlo mal.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
```

---

## Task 6: Precedencia — quién manda sobre qué campo

El corazón del asunto. Cada campo tiene un dueño y la regla del `TIMED` garantiza que el cron nunca empeore un dato escrito a mano.

**Files:**
- Modify: `actualizar_calendario.py` (añadir `en_rango` y `aplicar`)
- Test: `test_actualizar.py`

- [ ] **Step 1: Escribir los tests (fallan)**

Añadir a `test_actualizar.py`, antes del `if __name__`:

```python
# ------------------------------------------------------------------ precedencia
def test_aplicar():
    bloque("Precedencia de campos")
    import actualizar_calendario as ac
    cal = _cal_prueba()
    par = ac.emparejar(cal, _partidos_fixture())
    nuevo, cambios, avisos = ac.aplicar(cal, par)
    por_id = {m["id"]: m for m in nuevo}

    # 1) TIMED sobreescribe fecha y hora
    check("TIMED escribe la hora", por_id["L1"]["hora"] == "21:00",
          f'da {por_id["L1"]["hora"]}')
    check("TIMED escribe la fecha", por_id["L1"]["fecha"] == "Mié 26 ago 2026",
          f'da {por_id["L1"]["fecha"]}')
    check("TIMED actualiza la clave de orden", por_id["L1"]["sort"] == "2026-08-26")

    # 2) SCHEDULED no toca nada: no se degrada un rango escrito a mano
    check("SCHEDULED no toca la fecha", por_id["L5"]["fecha"] == "12/13 sep 2026",
          f'da {por_id["L5"]["fecha"]}')
    check("SCHEDULED no toca la hora", por_id["L5"]["hora"] == "TBD",
          f'da {por_id["L5"]["hora"]}')
    check("SCHEDULED sí registra el estado", por_id["L5"]["estado"] == "SCHEDULED")

    # 3) POSTPONED genera aviso
    check("POSTPONED genera aviso", "aplazado" in por_id["L16"]["aviso"],
          f'da {por_id["L16"]["aviso"]!r}')
    check("un partido normal no tiene aviso", por_id["L1"]["aviso"] == "")

    # 4) la eliminatoria recibe el rival, y nada más
    check("se rellena el rival de la eliminatoria", por_id["C6"]["rival"] == "Bayern",
          f'da {por_id["C6"]["rival"]}')
    check("rellenar el rival NO cambia el nivel", por_id["C6"]["nivel"] == 2,
          "renivelar es una decisión humana en POST, no del cron")
    check("rellenar el rival NO cambia la nota", por_id["C6"]["nota"] == "Teórico")

    # 5) un rival ya conocido no se sobreescribe con el nombre de la API
    check("el rival ya escrito se respeta", por_id["L1"]["rival"] == "Real Sociedad",
          f'da {por_id["L1"]["rival"]}')

    # 6) la Copa se queda intacta
    k1_antes = [m for m in _cal_prueba() if m["id"] == "K1"][0]
    check("la Copa del Rey no se toca", por_id["K1"] == k1_antes,
          "el emparejamiento no la encuentra, así que no debería cambiar nada")

    # 7) los campos de la persona no se tocan nunca
    antes = {m["id"]: m for m in _cal_prueba()}
    tocados = [f'{i}.{c}' for i in antes for c in ac.INTOCABLES
               if antes[i][c] != por_id[i][c]]
    check("ningún campo intocable ha cambiado", not tocados, str(tocados))

    # 8) el resultado sale ordenado por fecha
    check("el calendario sale ordenado",
          [m["sort"] for m in nuevo] == sorted(m["sort"] for m in nuevo))

    # 9) se informa de lo que se ha cambiado
    check("los cambios se reportan", any("L1" in c for c in cambios), str(cambios))


def test_aviso_de_jornada_movida():
    bloque("Aviso cuando una fecha SCHEDULED se sale del rango")
    import actualizar_calendario as ac

    # L5 tiene escrito "12/13 sep 2026"; la API lo pone en SCHEDULED el 20 de octubre
    cal = [m for m in _cal_prueba() if m["id"] == "L5"]
    lejos = [{"id": 1, "utcDate": "2026-10-20T18:00:00Z", "status": "SCHEDULED",
              "stage": "REGULAR_SEASON",
              "homeTeam": {"id": 86, "shortName": "Real Madrid"},
              "awayTeam": {"id": 87, "shortName": "Rayo Vallecano"}}]
    nuevo, cambios, avisos = ac.aplicar(cal, ac.emparejar(cal, lejos))
    check("avisa de que la jornada se ha movido", any("L5" in a for a in avisos), str(avisos))
    check("pero no sobreescribe la fecha", nuevo[0]["fecha"] == "12/13 sep 2026")

    # dentro del margen no debe avisar
    cerca = [dict(lejos[0], utcDate="2026-09-13T18:00:00Z")]
    _, _, avisos2 = ac.aplicar(cal, ac.emparejar(cal, cerca))
    check("no avisa si la fecha cae dentro del rango", not avisos2, str(avisos2))
```

Registrarlos en el `main`, tras `test_emparejar()`:

```python
    test_aplicar()
    test_aviso_de_jornada_movida()
```

- [ ] **Step 2: Ejecutar los tests para verificar que fallan**

Run: `python3 test_actualizar.py`

Esperado: `AttributeError: module 'actualizar_calendario' has no attribute 'aplicar'`.

- [ ] **Step 3: Escribir `en_rango` y `aplicar`**

Añadir a `actualizar_calendario.py`, después de `emparejar`:

```python
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
            if (f, h) != (m.get("fecha"), m.get("hora")):
                cambios.append(f'{m["id"]}: {m.get("fecha")} {m.get("hora")} -> {f} {h}')
                m["fecha"], m["hora"], m["sort"] = f, h, s
        elif d and estado == "SCHEDULED" and not en_rango(m, d):
            # No se sobreescribe (sería degradar un dato bueno con una estimación),
            # pero conviene enterarse: es la pista de que la jornada se ha movido.
            avisos.append(f'{m["id"]}: la API apunta al {d:%d/%m/%Y},'
                          f' fuera de "{m.get("fecha")}"')

        m["aviso"] = AVISOS.get(estado, "")
        nuevo.append(m)

    nuevo.sort(key=lambda m: m["sort"])
    return nuevo, cambios, avisos
```

- [ ] **Step 4: Ejecutar los tests para verificar que pasan**

Run: `python3 test_actualizar.py`

Esperado: los dieciséis checks de los dos bloques de precedencia en verde.

- [ ] **Step 5: Commit**

```bash
git add actualizar_calendario.py fechas.py test_actualizar.py
git commit -m "$(cat <<'MSG'
Precedencia: solo las fechas firmes sobreescriben

La regla central es que el cron no degrada un dato bueno. Un rango escrito a
mano como "12/13 sep 2026" es informacion real; una fecha SCHEDULED de la API
es una estimacion peor. Solo se escribe cuando la API la da por finalizada.

Si una fecha SCHEDULED se sale del rango escrito, no se sobreescribe pero se
avisa: es la pista temprana de que LaLiga ha movido la jornada.

El rival de las eliminatorias se rellena como etiqueta y nada mas. Renivelar
el bloque cuando se conoce un rival sigue siendo decision humana en POST.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
```

---

## Task 7: Validaciones antes de escribir

La red de seguridad: si la actualización toca algo que no le corresponde, no se escribe nada.

**Files:**
- Modify: `actualizar_calendario.py` (añadir `validar`)
- Test: `test_actualizar.py`

- [ ] **Step 1: Escribir los tests (fallan)**

Añadir a `test_actualizar.py`, antes del `if __name__`:

```python
# ------------------------------------------------------------------ validaciones
def test_validar():
    bloque("Validaciones previas a escribir")
    import actualizar_calendario as ac
    cal = _cal_prueba()

    check("un calendario sin cambios valida", not ac.validar(cal, [dict(m) for m in cal]))

    nuevo, _, _ = ac.aplicar(cal, ac.emparejar(cal, _partidos_fixture()))
    check("una actualización normal valida", not ac.validar(cal, nuevo),
          str(ac.validar(cal, nuevo)))

    falta = [dict(m) for m in cal if m["id"] != "L1"]
    p = ac.validar(cal, falta)
    check("detecta un partido que desaparece", any("L1" in x for x in p), str(p))

    sobra = [dict(m) for m in cal] + [dict(cal[0], id="ZZ")]
    check("detecta un partido que aparece de la nada",
          any("ZZ" in x for x in ac.validar(cal, sobra)))

    for campo, valor in (("seats", 1), ("nivel", 1), ("nota", "otra cosa"),
                         ("bloque", "EURO"), ("api_team", 999)):
        tocado = [dict(m) for m in cal]
        tocado[0][campo] = valor
        p = ac.validar(cal, tocado)
        check(f"detecta que ha cambiado {campo}", any(campo in x for x in p), str(p))

    menos = [dict(m) for m in cal]
    menos[0]["seats"] = 0
    check("detecta que cambian los asientos de un bloque",
          any("asientos" in x for x in ac.validar(cal, menos)))
```

Registrarlo en el `main`, tras `test_aviso_de_jornada_movida()`:

```python
    test_validar()
```

- [ ] **Step 2: Ejecutar los tests para verificar que fallan**

Run: `python3 test_actualizar.py`

Esperado: `AttributeError: module 'actualizar_calendario' has no attribute 'validar'`.

- [ ] **Step 3: Escribir `validar`**

Añadir a `actualizar_calendario.py`, después de `aplicar`:

```python
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
```

- [ ] **Step 4: Ejecutar los tests para verificar que pasan**

Run: `python3 test_actualizar.py`

Esperado: los diez checks del bloque de validaciones en verde.

- [ ] **Step 5: Commit**

```bash
git add actualizar_calendario.py test_actualizar.py
git commit -m "$(cat <<'MSG'
Valida el calendario antes de escribirlo

La actualizacion solo deberia mover fechas, horas, rivales por determinar y
avisos. Si ha tocado cualquier otra cosa (un nivel, unos asientos, un partido
que desaparece), no se escribe nada.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
```

---

## Task 8: Cliente de la API y línea de comandos

La capa de I/O: pedir los datos, aguantar los fallos con dignidad y escribir el fichero de una sola vez.

**Files:**
- Modify: `actualizar_calendario.py` (añadir `pedir`, `escribir_atomico`, `main`)
- Test: `test_actualizar.py`

- [ ] **Step 1: Escribir los tests (fallan)**

Añadir a `test_actualizar.py`, antes del `if __name__`:

```python
# ------------------------------------------------------- respuestas degradadas
def test_respuestas_malas():
    bloque("Respuestas de la API que no son de fiar")
    import actualizar_calendario as ac

    def falla(nombre, cuerpo):
        try:
            ac.partidos_de(cuerpo)
            check(nombre, False, "debería haber abortado y no lo hizo")
        except ac.RespuestaMala:
            check(nombre, True)

    falla("aborta si el cuerpo no es un objeto", [])
    falla("aborta si no hay lista 'matches'", {"resultSet": {"count": 0}})
    falla("aborta si 'matches' no es una lista", {"matches": "vaya"})
    falla("aborta si la respuesta viene vacía", {"matches": []})
    falla("aborta si vienen menos partidos de los esperados",
          {"matches": [{"id": i} for i in range(ac.MIN_PARTIDOS - 1)]})

    buena = {"matches": [{"id": i} for i in range(ac.MIN_PARTIDOS)]}
    check("acepta una respuesta con partidos de sobra",
          len(ac.partidos_de(buena)) == ac.MIN_PARTIDOS)

    # El fixture sintético tiene menos partidos que el mínimo (le bastan 8 para
    # probar los casos), así que solo se comprueba su forma.
    fx = json.load(open("tests/respuesta_api.json"))
    check("el fixture sintético tiene la forma que espera el script",
          isinstance(fx.get("matches"), list) and len(fx["matches"]) > 0)

    # Si ya se ha capturado una respuesta real (tarea 10), se comprueba que trae
    # los campos de los que depende el código. Es la prueba de que el esquema
    # supuesto en el fixture coincide con el de verdad.
    if os.path.exists("tests/respuesta_real.json"):
        real = json.load(open("tests/respuesta_real.json"))
        try:
            ps = ac.partidos_de(real)
            check("la respuesta real pasa la validación", True)
        except ac.RespuestaMala as e:
            check("la respuesta real pasa la validación", False, str(e))
            ps = []
        for campo in ("utcDate", "status", "homeTeam", "awayTeam", "competition"):
            check(f"la respuesta real trae el campo {campo}",
                  all(campo in p for p in ps), "el esquema de la API ha cambiado")
        check("la respuesta real trae stage en los partidos de Champions",
              all("stage" in p for p in ps
                  if (p.get("competition") or {}).get("code") == "CL"))
        check("el Madrid aparece como local en varios partidos",
              sum(1 for p in ps if (p.get("homeTeam") or {}).get("id") == ac.ID_MADRID) >= 19,
              "¿es correcto ID_MADRID?")


def test_escritura_atomica():
    bloque("Escritura del calendario")
    import actualizar_calendario as ac, tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "cal.json")
    datos = _cal_prueba()
    ac.escribir_atomico(p, datos)
    check("escribe un JSON que se puede volver a leer",
          json.load(open(p, encoding="utf-8")) == datos)
    check("no deja ficheros temporales al lado",
          os.listdir(d) == ["cal.json"], str(os.listdir(d)))
```

Registrarlos en el `main`, tras `test_validar()`:

```python
    test_respuestas_malas()
    test_escritura_atomica()
```

- [ ] **Step 2: Ejecutar los tests para verificar que fallan**

Run: `python3 test_actualizar.py`

Esperado: `AttributeError: module 'actualizar_calendario' has no attribute 'partidos_de'`.

- [ ] **Step 3: Escribir el cliente y el `main`**

Añadir a `actualizar_calendario.py`, después de `validar`:

```python
class RespuestaMala(Exception):
    """La API ha contestado algo que no se puede usar. No se escribe nada."""


def partidos_de(cuerpo):
    """Extrae la lista de partidos de la respuesta, o revienta con RespuestaMala.

    Una respuesta corta es más peligrosa que un error de red: si la API devuelve
    200 con tres partidos, escribir el resultado dejaría el calendario a medias.
    """
    if not isinstance(cuerpo, dict):
        raise RespuestaMala(f"la respuesta no es un objeto JSON, es {type(cuerpo).__name__}")
    partidos = cuerpo.get("matches")
    if not isinstance(partidos, list):
        raise RespuestaMala("la respuesta no trae una lista 'matches'")
    if len(partidos) < MIN_PARTIDOS:
        raise RespuestaMala(f"la API devuelve {len(partidos)} partidos, menos de los"
                            f" {MIN_PARTIDOS} esperados: no me fío")
    return partidos


def pedir(token, id_equipo=ID_MADRID, temporada=TEMPORADA):
    """Los partidos del equipo en la temporada. Una sola petición."""
    url = f"{BASE}/v4/teams/{id_equipo}/matches?season={temporada}"
    req = urllib.request.Request(url, headers={"X-Auth-Token": token,
                                               "User-Agent": "sorteo-bernabeu"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            cuerpo = json.load(r)
    except urllib.error.HTTPError as e:
        detalle = {401: "token inválido o ausente",
                   403: "el plan gratuito no cubre esto",
                   429: "límite de peticiones superado"}.get(e.code, e.reason)
        raise RespuestaMala(f"HTTP {e.code}: {detalle}")
    except urllib.error.URLError as e:
        raise RespuestaMala(f"no se pudo conectar: {e.reason}")
    except json.JSONDecodeError as e:
        raise RespuestaMala(f"la respuesta no es JSON válido: {e}")
    return partidos_de(cuerpo)


def escribir_atomico(ruta, datos):
    """Escribe el JSON en un temporal y lo renombra encima.

    El renombrado es atómico en el mismo sistema de ficheros, así que el
    calendario nunca queda a medias: o está el de antes, o está el nuevo entero.
    """
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, ruta)


def descubrir_ids(partidos):
    """Texto con los rivales en casa y su id, para rellenar api_team a mano."""
    lineas = ["Rivales en el Bernabéu esta temporada (para el campo api_team):", ""]
    vistos = set()
    for p in sorted(partidos, key=lambda p: p.get("utcDate") or ""):
        if (p.get("homeTeam") or {}).get("id") != ID_MADRID:
            continue
        v = p.get("awayTeam") or {}
        clave = (v.get("id"), p.get("stage"))
        if clave in vistos:
            continue
        vistos.add(clave)
        comp = (p.get("competition") or {}).get("code", "?")
        lineas.append(f'  api_team {str(v.get("id")):>6}   {comp:3}  {p.get("stage","")[:16]:16}'
                      f'  {v.get("shortName") or v.get("name")}')
    lineas += ["", "Y para las eliminatorias sin rival, el campo api_stage:",
               "  C5 -> PLAYOFFS    C6 -> LAST_16    C7 -> QUARTER_FINALS    C8 -> SEMI_FINALS"]
    return "\n".join(lineas)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice qué cambiaría, sin escribir nada")
    ap.add_argument("--descubrir-ids", action="store_true",
                    help="lista los ids de equipo de la API para rellenar api_team")
    ap.add_argument("--guardar-respuesta", metavar="FICHERO",
                    help="guarda la respuesta cruda de la API (para el fixture de test)")
    ap.add_argument("--token", default=os.environ.get("FOOTBALL_DATA_TOKEN"),
                    help="token de football-data.org (por defecto, $FOOTBALL_DATA_TOKEN)")
    a = ap.parse_args(argv)

    if not a.token:
        print("falta el token. Ponlo en la variable FOOTBALL_DATA_TOKEN o pásalo con --token."
              "\nSe consigue gratis en https://www.football-data.org/client/register",
              file=sys.stderr)
        return 2

    try:
        partidos = pedir(a.token)
    except RespuestaMala as e:
        print(f"la API no ha dado algo usable: {e}\nno se toca {CALENDARIO}", file=sys.stderr)
        return 1

    if a.guardar_respuesta:
        escribir_atomico(a.guardar_respuesta, {"matches": partidos})
        print(f"respuesta guardada en {a.guardar_respuesta} ({len(partidos)} partidos)")

    if a.descubrir_ids:
        print(descubrir_ids(partidos))
        return 0

    cal = json.load(open(CALENDARIO, encoding="utf-8"))
    emparejados = emparejar(cal, partidos)
    sin_emparejar = [m["id"] for m in cal if m["id"] not in emparejados]
    nuevo, cambios, avisos = aplicar(cal, emparejados)

    problemas = validar(cal, nuevo)
    if problemas:
        print("la actualización ha tocado algo que no debía, no se escribe nada:",
              file=sys.stderr)
        for p in problemas:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"{len(partidos)} partidos en la API, {len(emparejados)} emparejados"
          f" de los {len(cal)} del calendario")
    if sin_emparejar:
        print(f"sin correspondencia en la API: {', '.join(sin_emparejar)}")
    for c in cambios:
        print(f"  cambio  {c}")
    for v in avisos:
        print(f"  aviso   {v}")
    if not cambios:
        print("  nada que cambiar")

    if a.dry_run:
        print("\n--dry-run: no se ha escrito nada")
        return 0

    escribir_atomico(CALENDARIO, nuevo)
    print(f"\n{CALENDARIO} actualizado ({len(cambios)} cambio(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Ejecutar los tests para verificar que pasan**

Run: `python3 test_actualizar.py`

Esperado: los ocho checks de los dos bloques nuevos en verde, y `todo en orden`.

- [ ] **Step 5: Comprobar el CLI sin token y con token falso**

```bash
python3 actualizar_calendario.py --dry-run --token "" ; echo "salida: $?"
FOOTBALL_DATA_TOKEN=noesuntoken python3 actualizar_calendario.py --dry-run ; echo "salida: $?"
git status --short calendario.json
```

Esperado: el primero avisa de que falta el token y sale con `2`. El segundo falla con `HTTP 401: token inválido o ausente` y sale con `1`. Y `git status` no muestra nada: `calendario.json` no se ha tocado en ninguno de los dos casos.

- [ ] **Step 6: Commit**

```bash
git add actualizar_calendario.py test_actualizar.py
git commit -m "$(cat <<'MSG'
Cliente de la API y linea de comandos

Una sola peticion diaria a /v4/teams/{id}/matches. Cualquier respuesta que no
se entienda del todo aborta sin escribir: una respuesta corta es mas peligrosa
que un error de red, porque un 200 con tres partidos dejaria el calendario a
medias. La escritura es atomica via os.replace.

Trae --dry-run para probar sin riesgo y --descubrir-ids para rellenar los
api_team contra la propia API en vez de a memoria.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
```

---

## Task 9: El workflow de GitHub Actions

**Files:**
- Create: `.github/workflows/actualizar-calendario.yml`

- [ ] **Step 1: Escribir el workflow**

```yaml
name: Actualizar calendario

# El calendario de LaLiga se concreta jornada a jornada con unas dos semanas de
# antelación, así que se mira todas las noches. 03:17 UTC (madrugada en Madrid);
# el minuto no es redondo a propósito, porque los cron en punto coinciden con los
# picos de carga de Actions y se retrasan más.
on:
  schedule:
    - cron: "17 3 * * *"
  workflow_dispatch:

# Necesario para que el job pueda commitear el index.html regenerado.
permissions:
  contents: write

concurrency:
  group: actualizar-calendario
  cancel-in-progress: false

jobs:
  actualizar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      # Antes de tocar nada: si la API ha cambiado de formato, esto falla con un
      # mensaje claro en vez de dejar el calendario a medias.
      - name: Tests
        run: python3 test_actualizar.py

      - name: Actualizar el calendario
        env:
          FOOTBALL_DATA_TOKEN: ${{ secrets.FOOTBALL_DATA_TOKEN }}
        run: python3 actualizar_calendario.py | tee /tmp/salida.txt

      # hist2526.json está en .gitignore (es regenerable), así que en un checkout
      # limpio no existe y build.py no puede leerlo. Hay que generarlo antes.
      - name: Regenerar index.html
        run: |
          python3 hist2526.py
          python3 build.py

      # Solo se commitea si algo ha cambiado de verdad. Sin esta condición serían
      # 365 commits vacíos al año.
      - name: Commitear si hay cambios
        run: |
          if git diff --quiet -- calendario.json index.html; then
            echo "sin cambios: no hay nada que commitear"
            exit 0
          fi
          resumen=$(grep -c '^  cambio' /tmp/salida.txt || true)
          git config user.name  "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add calendario.json index.html
          {
            echo "Actualiza el calendario (${resumen:-0} cambio(s))"
            echo
            grep -E '^  (cambio|aviso)' /tmp/salida.txt || echo "(sin detalle)"
          } | git commit -F -
          git push
```

- [ ] **Step 2: Validar la sintaxis del YAML**

```bash
python3 -c "
import json, urllib.request, sys
# sin dependencias: se valida la indentación y que las claves clave estén
import re
s = open('.github/workflows/actualizar-calendario.yml').read()
for clave in ('on:', 'schedule:', 'workflow_dispatch:', 'permissions:',
              'contents: write', 'FOOTBALL_DATA_TOKEN', 'git push'):
    assert clave in s, clave
assert s.count('\t') == 0, 'hay tabuladores: el YAML no los admite'
print('el workflow tiene las claves necesarias y ningún tabulador')
"
```

Esperado: `el workflow tiene las claves necesarias y ningún tabulador`

- [ ] **Step 3: Simular localmente lo que hará el workflow**

Los tests y la regeneración se pueden ejecutar sin token; el paso de actualizar se
prueba con `--dry-run` en la tarea 10, cuando ya haya key.

Lo importante de este paso es reproducir la condición del runner: un checkout
limpio **no tiene `hist2526.json`**, porque está en `.gitignore`. Si `build.py`
se ejecuta sin él, el workflow falla.

```bash
mv hist2526.json /tmp/hist2526.bak
python3 build.py 2>&1 | tail -2 ; echo "salida sin hist2526.json: $?"
python3 hist2526.py >/dev/null && python3 build.py >/dev/null && echo "con hist2526.py delante: ok"
diff <(python3 -c "print(open('/tmp/hist2526.bak').read())") \
     <(python3 -c "print(open('hist2526.json').read())") >/dev/null \
     && echo "hist2526.py reproduce el mismo fichero"
python3 test_actualizar.py && git diff --stat -- index.html
```

Esperado: `build.py` falla a secas con un `FileNotFoundError: 'hist2526.json'`,
funciona con `hist2526.py` delante, el fichero regenerado es idéntico al que
había, los tests están en verde y `git diff` no muestra cambios en `index.html`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/actualizar-calendario.yml
git commit -m "$(cat <<'MSG'
Workflow nocturno que actualiza el calendario

Corre a las 03:17 UTC y tambien a mano desde la pestana Actions. Los tests van
primero: si la API cambia de formato, el resultado es un fallo claro y no un
calendario corrupto. Commitea solo si algo ha cambiado de verdad.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
```

---

## Task 10: Puesta en marcha y documentación

Los pasos que no puede dar el código, y el README al día.

**Files:**
- Modify: `calendario.json` (rellenar `api_team` y `api_stage`)
- Modify: `tests/respuesta_api.json` (sustituir por una respuesta real)
- Modify: `README.md`

- [ ] **Step 1: Conseguir el token (lo hace Pablo)**

Registrarse en https://www.football-data.org/client/register — es gratis, solo pide un email, y la key llega por correo.

Luego, en local:

```bash
export FOOTBALL_DATA_TOKEN="<la key>"
python3 -c "import os; print('token de', len(os.environ['FOOTBALL_DATA_TOKEN']), 'caracteres')"
```

- [ ] **Step 2: Confirmar el id del Real Madrid**

`ID_MADRID = 86` está escrito de memoria en `actualizar_calendario.py` y hay que verificarlo contra la API antes de fiarse:

```bash
curl -s -H "X-Auth-Token: $FOOTBALL_DATA_TOKEN" \
  "https://api.football-data.org/v4/competitions/PD/teams?season=2026" \
  | python3 -c "
import json, sys
for t in json.load(sys.stdin)['teams']:
    if 'Madrid' in t['name']:
        print(t['id'], t['name'])
"
```

Esperado: una línea `86 Real Madrid CF`. Si el id es otro, corregir `ID_MADRID` en `actualizar_calendario.py` y volver a ejecutar los tests.

- [ ] **Step 3: Descubrir los ids de los rivales**

```bash
python3 actualizar_calendario.py --descubrir-ids
```

Esperado: la lista de rivales en el Bernabéu con su `api_team`.

- [ ] **Step 4: Rellenar `api_team` y `api_stage` en `calendario.json`**

Con la salida del paso anterior, asignar a cada partido su `api_team`. Los seis sin rival conocido llevan `api_team: null` y el `api_stage` que corresponda:

| id | `api_stage` |
|---|---|
| `C5` | `PLAYOFFS` |
| `C6` | `LAST_16` |
| `C7` | `QUARTER_FINALS` |
| `C8` | `SEMI_FINALS` |
| `K1`, `K2` | `null` — Copa del Rey, fuera del plan gratuito |

Los ids concretos no se pueden escribir de antemano: salen del paso 3 y hay que
transcribirlos. El diccionario `IDS` de abajo tiene que acabar con **23 entradas**
— los 19 partidos de LaLiga en casa más `C1`–`C4` de Champions — emparejando cada
`id` del calendario con el `api_team` que imprimió `--descubrir-ids` para ese
rival. Las dos primeras están puestas como ejemplo del formato.

```bash
python3 - <<'PY'
import json
# Transcribir aquí los ids que ha impreso --descubrir-ids, emparejando cada
# partido del calendario con su rival. Deben quedar 23 entradas.
IDS = {
    "L1": 92,    # Real Sociedad
    "L5": 87,    # Rayo Vallecano
}
STAGES = {"C5": "PLAYOFFS", "C6": "LAST_16",
          "C7": "QUARTER_FINALS", "C8": "SEMI_FINALS"}
cal = json.load(open("calendario.json", encoding="utf-8"))
for m in cal:
    if m["id"] in IDS:
        m["api_team"] = IDS[m["id"]]
    if m["id"] in STAGES:
        m["api_stage"] = STAGES[m["id"]]
json.dump(cal, open("calendario.json", "w"), ensure_ascii=False, indent=1)
faltan = [m["id"] for m in cal
          if m["api_team"] is None and m["api_stage"] is None and m["comp"] != "COPA"]
print(f"{len(IDS)} ids transcritos (deben ser 23)")
print("sin emparejar y sin ser Copa:", faltan)
PY
```

Esperado: `23 ids transcritos (deben ser 23)` y `sin emparejar y sin ser Copa: []`.
La lista sale vacía porque los únicos partidos sin `api_team` ni `api_stage` son
`K1` y `K2`, que son de Copa del Rey y quedan excluidos a propósito.

- [ ] **Step 5: Probar la actualización en seco**

```bash
python3 actualizar_calendario.py --dry-run
git status --short calendario.json
```

Esperado: un resumen con los partidos emparejados y los cambios que haría, el aviso `--dry-run: no se ha escrito nada`, y `git status` limpio.

Revisar la lista de cambios a ojo antes de seguir. Debe emparejar **23**: los 19
partidos de LaLiga en casa y `C1`–`C4` de Champions. Los otros seis salen en la
línea "sin correspondencia en la API", y es lo correcto:

- `C5`–`C8` son eliminatorias que todavía no existen en el calendario de la UEFA;
  se emparejarán solas cuando se sorteen, gracias a su `api_stage`.
- `K1` y `K2` son Copa del Rey, que no cubre el plan gratuito, y se quedan a mano.

- [ ] **Step 6: Guardar una respuesta real y comprobar que el esquema coincide**

El fixture sintético se queda como está: los tests afirman cosas sobre sus ids
controlados. Lo que se captura ahora es una respuesta real **en un fichero
aparte**, y el test comprueba que trae los campos de los que depende el código.
Es la prueba de que el esquema supuesto es el de verdad.

```bash
python3 actualizar_calendario.py --guardar-respuesta tests/respuesta_real.json --dry-run >/dev/null
python3 -c "
import json
m = json.load(open('tests/respuesta_real.json'))['matches']
print(len(m), 'partidos guardados')
print('el Madrid es local en', sum(1 for p in m if p['homeTeam']['id'] == 86))
"
python3 test_actualizar.py
```

Esperado: unos 46 partidos, el Madrid local en 19 o más, y los tests en verde
incluidos los cinco checks nuevos de "la respuesta real".

Si alguno de esos checks falla, es información valiosa y no un test quisquilloso:
significa que la forma real de la respuesta no es la que se supuso. Ajustar el
código —nunca el test— hasta que pase.

- [ ] **Step 7: Actualizar de verdad y regenerar la web**

```bash
python3 actualizar_calendario.py
python3 build.py
git diff --stat
```

Esperado: `calendario.json` e `index.html` modificados. Abrir `index.html` y comprobar que las fechas nuevas se ven bien.

- [ ] **Step 8: Actualizar el README**

Sustituir la tabla de scripts y el bloque de comandos de la sección "Cómo está montado" por:

````markdown
## Cómo está montado

Los datos viven en tres ficheros y los scripts son de Python sin dependencias
externas (solo la librería estándar):

| Fichero | Qué es |
|---|---|
| `calendario.json` | Los 29 partidos: fecha, hora, rival, nivel, asientos. **Lo actualiza un cron cada noche.** |
| `reparto.json` | Quién va a cada partido. **Congelado**: la salida del sorteo, con los cambios de `POST` aplicados. |
| `hist2526.json` | La temporada 2025/26, que ya es historia. |

| Script | Qué hace |
|---|---|
| `sorteo.py` | Celebra el sorteo de la temporada. Escribe `reparto.json`. Se lanza **a mano**, una vez por temporada. |
| `actualizar_calendario.py` | Pide las fechas a football-data.org y actualiza `calendario.json`. Lo lanza el cron. |
| `hist2526.py` | Datos históricos de 2025/26. Escribe `hist2526.json`. |
| `build.py` | Cruza los tres JSON y genera `index.html`. |
| `test_actualizar.py` | Tests. `python3 test_actualizar.py`. |

```bash
python3 actualizar_calendario.py --dry-run   # ver qué cambiaría, sin tocar nada
python3 actualizar_calendario.py             # actualizar el calendario
python3 build.py                             # regenerar index.html
```

### Por qué el calendario y el reparto están separados

Porque las fechas son una **entrada** del sorteo, no un adorno. `sorteo.py` ordena
los partidos por fecha (`M.sort`) y las reglas 3 y 4 de `score()` —"nadie tres
partidos seguidos", "sin sequías largas"— se evalúan sobre ese orden. Si un proceso
automático cambiara una fecha y volviera a lanzar el sorteo, el reparto podría salir
distinto: otro Derbi, otro Clásico, otras parejas.

Así que el fichero que toca el cron, `calendario.json`, **no contiene asistentes**.
No tiene forma de alterar el reparto. Y `sorteo.py` no se ejecuta nunca de forma
automática.

Dos reglas más que conviene conocer:

- **El cron solo escribe fechas que la API da por finalizadas** (`status: TIMED`).
  Un rango escrito a mano como "12/13 sep 2026" es información real y no se
  degrada con una estimación. Si la API mueve una jornada fuera de ese rango, lo
  avisa en el mensaje del commit sin sobreescribir nada.
- **Rellenar el rival de una eliminatoria no cambia su nivel.** Cuando se conoce
  el rival, renivelar el bloque sigue siendo una decisión que se toma a mano en
  `POST`, como se hizo con Inter, Leipzig, PSV y LASK.

La Copa del Rey (`K1`, `K2`) no la cubre el plan gratuito de la API, así que esas
dos fechas se siguen poniendo a mano.
````

Y añadir al final del `footer` de `build.py` (el texto de fuentes, alrededor de la línea 338) la frase de la actualización automática:

```bash
python3 - <<'PY'
import io
p = "build.py"
s = io.open(p, encoding="utf-8").read()
viejo = "  Documento de consulta — si hay cambios o intercambios, se anotan aparte."
nuevo = ("  Las fechas y horas se actualizan solas cada noche desde\n"
         '  <a href="https://www.football-data.org/">football-data.org</a>;'
         " las que aún no son firmes se muestran como rango.\n"
         "  Documento de consulta — si hay cambios o intercambios, se anotan aparte.")
assert viejo in s
io.open(p, "w", encoding="utf-8").write(s.replace(viejo, nuevo))
print("footer actualizado")
PY
python3 build.py >/dev/null && grep -c "football-data" index.html
```

Esperado: `footer actualizado` y `1`.

- [ ] **Step 9: Guardar el token como secret del repo (lo hace Pablo)**

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**

- Name: `FOOTBALL_DATA_TOKEN`
- Secret: la key

- [ ] **Step 10: Commit y primera ejecución del workflow**

```bash
python3 test_actualizar.py
git add calendario.json index.html README.md build.py tests/respuesta_api.json
git commit -m "$(cat <<'MSG'
Pone en marcha la actualizacion automatica del calendario

Rellena los api_team con los ids reales de la API, sustituye el fixture
sintetico por una respuesta real y documenta el nuevo flujo en el README,
incluido el por que de separar calendario y reparto.

Co-Authored-By: Claude <noreply@anthropic.com>
MSG
)"
git push
```

Después, en GitHub: pestaña **Actions → Actualizar calendario → Run workflow**, para comprobar que funciona sin esperar a la madrugada.

Esperado: el workflow en verde. Si no había nada que actualizar, el paso de commit dirá `sin cambios: no hay nada que commitear`, que también es un éxito.

- [ ] **Step 11: Verificar que la web publicada se ha actualizado**

Esperar uno o dos minutos a que Pages redespliegue y abrir
https://pablorenedolastra.github.io/Sorteo-Bernabeu/

Comprobar que las fechas coinciden con las de `index.html` en local.

---

## Notas para quien ejecute el plan

**Si el test de regresión de la tarea 1 falla, para.** Significa que separar los
datos ha movido el sorteo, que es exactamente lo que el diseño trata de evitar. No
se arregla ajustando el test.

**Los tests van antes que el código en todas las tareas.** El paso de "verificar
que falla" no es una formalidad: si un test pasa antes de escribir la
implementación, es que no está comprobando lo que crees.

**GitHub desactiva los workflows programados tras 60 días sin actividad en el
repositorio** y avisa por email. Fuera de temporada puede pasar; se reactiva con un
clic desde la pestaña Actions.
