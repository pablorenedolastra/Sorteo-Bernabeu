# Actualización diaria del calendario

**Fecha:** 7 septiembre 2026
**Estado:** aprobado, pendiente de plan de implementación

## Objetivo

Que las fechas y horas de los partidos en
[la web](https://pablorenedolastra.github.io/Sorteo-Bernabeu/) se actualicen solas
cada noche, sin intervención manual. Hoy, de los 29 partidos, **19 tienen la hora
en `TBD` y 21 tienen la fecha como un rango** ("12/13 sep 2026"); 17 arrastran las
dos cosas a la vez. Es así porque LaLiga concreta cada jornada con unas dos semanas
de antelación, y esos datos hay que ir metiéndolos a mano: en la práctica no se hace.

## El problema de fondo, que no es el que parece

El encargo suena a "un cron que refresque unos datos". Pero al mirar el código
aparece algo más serio: **`sorteo.py` recalcula el sorteo entero cada vez que se
ejecuta, y las fechas son una de sus entradas.**

`M.sort(key=lambda x: x[4])` ordena el calendario por fecha, y las reglas 3 y 4 de
`score()` —"nadie tres partidos seguidos" y "sin sequías largas"— se evalúan sobre
ese orden. El sorteo es determinista (semilla `20262027`), pero determinista no es
lo mismo que estable: si un proceso automático cambia la fecha de un partido y
vuelve a lanzar `sorteo.py`, el optimizador explora el espacio con otra función de
coste y **el reparto puede salir distinto**. Otro Derbi, otro Clásico, otras
parejas. Y encima los cambios de `POST`, cuadrados a mano y a petición expresa,
se aplicarían sobre un reparto que ya no es el que tenían debajo.

Un cron ingenuo sobre el diseño actual no actualiza fechas: rebaraja el sorteo cada
vez que LaLiga confirma una jornada.

Por tanto el trabajo real es **separar el calendario del reparto**. La
actualización diaria es la consecuencia, no la causa.

## Decisiones tomadas

| Decisión | Elegido | Descartado |
|---|---|---|
| Alcance | fecha, hora y rival de eliminatorias | resultados, confirmar teóricos |
| Fuente de datos | API football-data.org | API-Football, scraping, avisar y editar a mano |
| Ejecución | GitHub Actions programado | launchd en el Mac |
| Arquitectura | congelar el reparto en un fichero | recalcular con `assert`, parchear el HTML |

Sobre la fuente: el plan gratuito de football-data.org cubre LaLiga y Champions
([coverage](https://www.football-data.org/coverage)) con 10 peticiones por minuto
([policies](https://docs.football-data.org/general/v4/policies.html)). **No cubre
Copa del Rey**, así que K1 y K2 se quedan a mano. Son 2 partidos de 29 y además
teóricos.

El hallazgo que hace viable el diseño está en el campo `status` del recurso
[match](https://docs.football-data.org/general/v4/match.html): `SCHEDULED` es fecha
aproximada y `TIMED` es día y hora finalizados. La API distingue sola lo provisional
de lo confirmado, así que no hay que inventar heurísticas para adivinarlo.

## Arquitectura

Hoy la tabla `M` de `sorteo.py` mezcla tres clases de dato con vidas muy distintas.
El diseño las separa en tres ficheros con un dueño único cada uno:

| Fichero | Dueño | Cuándo cambia | En git |
|---|---|---|---|
| `calendario.json` | el cron | a diario | sí |
| `reparto.json` | `sorteo.py` | una vez por temporada | sí |
| `hist2526.json` | `hist2526.py` | ya no cambia | como hoy |

```
                    ┌─ actualizar_calendario.py ──┐
football-data.org ──┤ 1 petición: /v4/teams/{md}/ │──> calendario.json
                    └─  matches?season=2026 ──────┘         │
                                                            ▼
                            reparto.json ──────────>  build.py  ──> index.html
                            hist2526.json ─────────>     │
                                                         ▼
                                        git commit + push (solo si cambió)
                                                         │
                                                         ▼
                                                  GitHub Pages
```

Una sola petición diaria: `/v4/teams/{id-madrid}/matches?season=2026` devuelve todos
los partidos de la temporada en las competiciones cubiertas.

**`sorteo.py` no se modifica salvo su salida** y no se ejecuta nunca desde el cron.
Sigue siendo el registro de cómo se celebró el sorteo, con sus comentarios y su
`POST`. En vez de `sorteo.json` escribe dos ficheros: `reparto.json` y un
`calendario.json` inicial con los campos que ya conoce y `api_team`/`api_stage` a
`null`. Esos dos se rellenan después una única vez (ver *Emparejamiento*) y a
partir de ahí sobreviven a cualquier regeneración, porque el cron no los toca.
`sorteo.py` lo lanza una persona, a mano, solo si algún año se rehace el sorteo.

El cron no puede alterar el reparto porque no tiene ningún camino para hacerlo: no
importa `sorteo.py`, no ejecuta el optimizador y escribe en un fichero que no
contiene asistentes.

### `calendario.json`

Lista de 29 objetos. Campos mutables (los toca el cron):

- `fecha` — texto ya formateado en español, p. ej. `"Mié 26 ago 2026"`
- `hora` — `"21:00"` o `"TBD"`
- `sort` — clave ISO de ordenación, `"2026-08-26"`
- `rival` — nombre del rival
- `estado` — el `status` de la API, para saber si la fecha es firme
- `aviso` — texto generado si el partido está aplazado, suspendido o cancelado

Campos estables (los pone una persona, la API no los toca jamás):

- `id`, `comp`, `ronda`, `nivel`, `nota`, `seats`, `bloque`
- `api_team` — id numérico del rival en football-data.org, o `null` en las
  eliminatorias sin rival
- `api_stage` — ronda de la API para las eliminatorias (`PLAYOFFS`, `LAST_16`,
  `QUARTER_FINALS`, `SEMI_FINALS`), o `null`

### `reparto.json`

Mapa plano `id → lista de asistentes`, con `POST` ya aplicado:

```json
{"L1": ["Alberto", "Víctor"], "L3": ["Jorge"], "C1": ["Jorge", "Pablo"]}
```

Pasa a estar en git. Hoy `sorteo.json` está en `.gitignore`, lo cual es correcto
mientras es un fichero regenerable y deja de serlo en el momento en que es la
fuente de verdad del reparto.

## `actualizar_calendario.py`

### Emparejamiento

Por id numérico de equipo, **nunca por nombre**. La API dice "Real Sociedad de
Fútbol" y "Club Atlético de Madrid" donde el proyecto dice "Real Sociedad" y
"Atlético de Madrid"; normalizar cadenas para que cuadren es una fuente inagotable
de bugs.

- **Partidos con rival conocido:** el partido de la API donde el Madrid es
  `homeTeam` y `awayTeam.id == api_team`. Que el Madrid sea el local desambigua
  solo las dos vueltas de LaLiga.
- **Eliminatorias sin rival (C5–C8):** por `api_stage`, cogiendo el partido de esa
  ronda en el Bernabéu cuando exista.
- **K1 y K2 (Copa del Rey):** no aparecen en la API con el plan gratuito. El
  emparejamiento no los encuentra y por tanto no los toca. No hace falta ningún
  mecanismo de bloqueo: quedan protegidos por construcción.

Los `api_team` no se escriben de memoria. El script incluye un modo
`--descubrir-ids` que lista los partidos del Madrid en casa con el id y el nombre
de cada rival; con esa salida se rellenan los `api_team` una sola vez y
verificados contra la propia API.

### Precedencia de campos

| Campo | Dueño | Regla de escritura |
|---|---|---|
| `fecha`, `hora`, `sort` | la API | **solo si `status == TIMED`** |
| `rival` | la API | solo si el valor actual es `"Rival por determinar"` |
| `estado`, `aviso` | la API | siempre |
| `nivel`, `nota`, `seats`, `ronda`, `bloque`, `comp` | la persona | nunca |
| asistentes | `reparto.json` | el cron no los ve |

La regla del `TIMED` es la central: **el cron nunca degrada un dato bueno.** Un
rango escrito a mano como "12/13 sep 2026" es información real y útil; una fecha
`SCHEDULED` de la API es una estimación que sería peor. Solo se escribe cuando la
fecha está finalizada.

Con un matiz para no perder señal: si el estado es `SCHEDULED` y la fecha de la API
cae **fuera** del rango que hay escrito, no se sobreescribe, pero se registra como
aviso en el resumen. Es la pista temprana de que LaLiga ha movido la jornada.

Sobre el rival: el cron rellena la **etiqueta**, nada más. Cuando se conoce un
rival su nivel real cambia —como ocurrió con Inter, Leipzig, PSV y LASK tras el
sorteo de la fase liga— y renivelar el bloque es una decisión humana en `POST`, no
algo que deba hacer un script de madrugada. El script no toca `nivel` nunca.

`POSTPONED`, `SUSPENDED` y `CANCELLED` generan texto en `aviso`, un campo propio de
la API que `build.py` muestra en la fila junto a `nota`. Así no hay conflicto por la
propiedad de `nota`, cuyo texto sigue siendo de la persona.

### Detalles que rompen este tipo de scripts en CI

- `utcDate` viene en UTC y hay que convertirlo a hora de Madrid. Con `zoneinfo` de
  la librería estándar, para no añadir dependencias al proyecto.
- El formato `"Mié 26 ago 2026"` se genera con tablas propias de días y meses en
  español. **No** con `locale.setlocale(LC_TIME, "es_ES")`: ese locale no existe en
  el runner de Ubuntu y el script fallaría solo en producción.

### Errores

El principio: **un fallo del cron nunca debe empeorar la web.** Una fecha
desactualizada es mejor que una fecha inventada, y mucho mejor que un `index.html`
roto.

- Si la API no responde, devuelve 429, 5xx o un cuerpo que no es el esperado, el
  script **aborta sin escribir nada**. `index.html` se queda como estaba y GitHub
  avisa por email del workflow fallido.
- Si la API responde bien pero con menos partidos de los esperados —la respuesta
  degradada típica— también aborta. Es el caso que arrasaría el calendario en
  silencio.
- El calendario nuevo se construye entero en memoria, se valida y solo entonces se
  escribe. El fichero no queda nunca a medias.
- Validaciones previas a escribir: están los 29 ids, ningún `seats` ni `nivel` ha
  cambiado, y la suma de asientos por bloque es la de siempre.
- `build.py` comprueba que todo id de `calendario.json` tiene entrada en
  `reparto.json`, y falla si no.

Y un `--dry-run` que imprime lo que cambiaría sin escribir nada, para probarlo en
local sin riesgo.

## El workflow

`.github/workflows/actualizar-calendario.yml`

- `schedule: "17 3 * * *"` (03:17 UTC, madrugada en Madrid). Minuto no redondo a
  propósito: los cron en punto coinciden con los picos de carga de Actions.
- `workflow_dispatch` para poder lanzarlo a mano desde la pestaña Actions.
- `permissions: contents: write`, necesario para commitear.
- Token en `secrets.FOOTBALL_DATA_TOKEN`. Nunca en el repo.
- Pasos: checkout → `python3 test_actualizar.py` → `python3 actualizar_calendario.py`
  → `python3 build.py` → commit y push **solo si hay cambios**. Sin esa condición
  serían 365 commits vacíos al año.
- El mensaje de commit resume qué cambió, para que el historial se pueda leer.

Los tests corren antes de tocar nada: el día que la API cambie de formato, el
resultado será un fallo claro y no un calendario corrupto.

## Pruebas

El proyecto no tiene tests y no se va a montar pytest para esto. Pero el parseo de
la API tiene que poder comprobarse sin llamar a la API.

`tests/respuesta_api.json` guarda una respuesta real de la API.
`test_actualizar.py` verifica cinco casos, sin dependencias, ejecutable con
`python3 test_actualizar.py`:

1. Un partido `TIMED` sobreescribe fecha y hora.
2. Un partido `SCHEDULED` no sobreescribe nada.
3. Un `POSTPONED` genera texto en `aviso`.
4. Una eliminatoria con rival conocido rellena `rival` y no toca `nivel`.
5. Una respuesta vacía o corta aborta sin escribir.

## Trabajo manual necesario

Dos cosas que no puede hacer el código:

1. Registrarse en football-data.org y obtener la key (gratis, solo email).
2. Pegarla en Settings → Secrets and variables → Actions del repo, como
   `FOOTBALL_DATA_TOKEN`.

Y una tercera, una única vez: ejecutar `--descubrir-ids` y volcar los `api_team` en
`calendario.json`.

## Fuera de alcance

- Resultados de los partidos.
- Confirmar o descartar los partidos teóricos según cómo vaya el Madrid.
- Recalcular niveles al conocerse un rival, y renivelar bloques. Sigue siendo una
  decisión humana en `POST`.
- Copa del Rey (K1, K2): no la cubre el plan gratuito.
- La temporada 2025/26 (`hist2526.py`), que es historia y no cambia.

## Riesgos conocidos

**GitHub desactiva los workflows programados tras 60 días sin actividad en el
repositorio** y avisa por email. Fuera de temporada puede pasar. Se reactiva con un
clic, pero conviene saberlo de antemano.

**La API puede cambiar de formato.** Mitigado: los tests corren antes que nada y el
script aborta sin escribir ante cualquier respuesta que no reconozca.

**El nombre del rival que da la API puede no gustar** ("Real Sociedad de Fútbol").
El campo `rival` solo se escribe en eliminatorias sin rival conocido, y siempre se
puede corregir a mano: al dejar de ser `"Rival por determinar"`, el cron no vuelve
a tocarlo.
