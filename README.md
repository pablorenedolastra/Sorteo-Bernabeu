# Sorteo Bernabéu

Web de consulta del reparto de los dos abonos del Bernabéu entre **Pablo, Víctor,
Jorge y Alberto**. Publicada en GitHub Pages:

**https://pablorenedolastra.github.io/Sorteo-Bernabeu/**

> `index.html` es un **fichero generado**. No lo edites a mano: los totales, los
> porcentajes, la matriz de parejas y varias frases de las reglas se calculan a
> partir de los datos. Si lo tocas directamente, la página empieza a mentir.

## Cómo está montado

Tres scripts de Python sin dependencias externas (solo la librería estándar):

| Fichero | Qué hace |
|---|---|
| `sorteo.py` | Datos y sorteo de la temporada **2026/27**. Escribe `sorteo.json`. |
| `hist2526.py` | Datos históricos de la temporada **2025/26**. Escribe `hist2526.json`. |
| `build.py` | Lee los dos JSON y genera `index.html` (una sola página, sin dependencias). |

```bash
python3 sorteo.py && python3 hist2526.py && python3 build.py
```

`build.py` deja el resultado en `index.html`. La página es autocontenida: todo el
CSS y el JS van inline, no carga nada de fuera y funciona abriéndola en local.

## Las reglas del reparto

Quién paga qué: **Pablo 1/3, Víctor 1/3, Jorge 1/6, Alberto 1/6**. Las entradas se
reparten en esa proporción, pero con una separación importante:

- **Bloque LaLiga** — se equilibra por niveles *consigo mismo*. La cuota se aplica
  por separado dentro del nivel 1 (partidazos), el 2 (medios) y el 3 (normales).
  Los cupos están en `LIGA_Q` en `sorteo.py`.
- **Bloque Champions + Copa** — se reparte por cuota total (`EURO_Q`), sin niveles
  en el sorteo, porque cuando se hizo no se sabía qué partidos iban a ser buenos.
  Celebrado ya el sorteo de la fase liga (27 ago 2026), los cuatro partidos con
  rival conocido tienen su nivel de verdad y el bloque se **niveló a mano** con un
  intercambio en `POST` (ver más abajo). Las eliminatorias (`C5`–`C8`, `K1`, `K2`)
  siguen con nivel provisional hasta que se conozca el cruce.

Los dos bloques no se mezclan: cambiar algo en Champions no debe descuadrar la Liga.

Restricciones adicionales, todas en la función `score()` de `sorteo.py`:

- Alberto va preferentemente con Pablo o con Jorge. El tope eran 2 veces con
  Víctor; ahora son **3**, por el reequilibrio que se explica más abajo.
- El Derbi y el Clásico son los dos únicos nivel 1 garantizados: 4 asientos, uno
  por cabeza.
- Nadie tres partidos seguidos; sin sequías largas. Ojo: son penalizaciones que el
  optimizador minimiza, no prohibiciones. Pablo y Víctor van a 18 y 19 de los 29
  partidos, así que encadenar tres es casi inevitable y de hecho pasa 9 veces.
- Las parejas se acercan al reparto más variado posible (`PAIR_T`), que no es
  uniforme: como Pablo y Víctor van a 19 de 29 partidos, coinciden por fuerza un
  mínimo de 9 veces.
- La semifinal de Copa no repite exactamente la pareja del Derbi ni la del Clásico.

### Las parejas no son seis números libres

Conviene saberlo antes de tocar `PAIR_T`. Cada uno tiene un número fijo de partidos
con pareja (Pablo 19, Víctor 19, Alberto 10, y Jorge 8 porque el Málaga va solo), y
eso son cuatro ecuaciones. Todo el sistema queda determinado por dos números,
`j` = Pablo+Jorge y `a` = Pablo+Alberto:

    Pablo+Víctor  = 19 - j - a          Víctor+Jorge   = a - 1
    Alberto+Jorge =  9 - j - a          Alberto+Víctor = j + 1

La última es la que duele: **cada partido que Pablo gana con Jorge obliga a uno más
de Alberto con Víctor**, que es lo que Alberto pidió evitar. Equilibrar del todo a
Pablo (`j = a`) exigiría Alberto+Víctor = 4, el doble del tope original. Por eso el
reequilibrio se quedó en `j=2, a=5`, con Alberto+Víctor en 3.

Casos particulares fijados a mano en `FIXED` (entran *antes* de optimizar, el
sorteo se construye respetándolos):

- `L3` — 30 ago, Málaga: solo hay **una entrada**, va Jorge.
- `L1` — 26 ago, Real Sociedad: Alberto + Víctor (Pablo no está).

## Cómo hacer un cambio

**Nunca edites `index.html`.** Según el tipo de cambio:

### Cambiar quién va a un partido de 2026/27

Añade una entrada a `POST` en `sorteo.py`, que se aplica *después* del sorteo y no
re-optimiza nada, para no descolocar el resto del calendario. Hay dos tipos y no
conviene confundirlos:

```python
POST = {"L8":  ["Víctor", "Jorge"],     # sustitución: entra Jorge en lugar de Pablo
        "L16": ["Pablo", "Jorge"],      # intercambio: Jorge entra por Alberto ...
        "L19": ["Alberto", "Víctor"],   #              ... y Alberto ocupa su sitio
        "C2":  ["Víctor", "Jorge"],     # intercambio: Jorge entra por Pablo ...
        "C4":  ["Víctor", "Pablo"]}     #              ... y Pablo ocupa su sitio
```

- **Sustitución directa** — alguien entra en el sitio de otro. **Descuadra la cuota
  a propósito.** Es el caso del Villarreal (`L8`).
- **Intercambio** — dos personas se cambian el sitio entre dos partidos *del mismo
  bloque*. **No mueve ningún total**, solo cambia con quién va cada uno. Si además
  los dos partidos son del mismo nivel, tampoco mueve ninguna cuota: es el caso de
  Osasuna/Levante (`L16` y `L19`), el reequilibrio entre Alberto y Jorge. Si son de
  niveles distintos *dentro del bloque EURO* tampoco pasa nada, porque ese bloque se
  reparte por cuota total y no por niveles: es el caso de Leipzig/LASK (`C2` y `C4`),
  el nivelado de Champions. Lo que **no** vale es cruzar dos partidos de Liga de
  niveles distintos, porque ahí la cuota sí es por nivel.

  Este es el mecanismo para mover parejas o niveles sin romper el reparto: busca dos
  partidos compatibles y cruza a dos personas. Es preferible a reoptimizar, sobre
  todo con la temporada empezada.

Si el cambio rompe un cupo de forma relevante, dilo en la respuesta y déjalo escrito
en el comentario de `POST`, que es donde queda el rastro. La página ya no publica las
reglas del sorteo, así que ahí no hay nada que actualizar.

Alternativa: si quieres que el sorteo *respete* la restricción y reequilibre lo
demás, mete el partido en `FIXED` en vez de en `POST`. Ojo: eso vuelve a barajar
el resto de asignaciones.

### Corregir la temporada 2025/26

Edita la lista `H` en `hist2526.py` y actualiza el dict `esperado` del final, que
es la comprobación contra el resumen original del Excel.

### Reetiquetar los niveles de Champions (hecho para la fase liga)

Los niveles de Champions **no entran en `GROUPS`**: el bloque EURO agrupa todos sus
partidos sin mirar el nivel. Por eso cambiar el campo `nivel` de una fila `C*` no
rebaraja nada — ni la Liga ni el propio bloque EURO. Es un cambio solo de etiqueta.

Ya está aplicado para los cuatro partidos de la fase liga: Inter y Leipzig nivel 2,
PSV y LASK nivel 3. Lo que sí hubo que hacer aparte es **nivelar** el reparto dentro
de esos niveles, con un intercambio en `POST`. Cuando se conozcan los cruces de
eliminatoria, mismo procedimiento: reetiquetar `C5`–`C8` y, si algún nivel queda
desigual, corregirlo con un intercambio, nunca reoptimizando.

El objetivo de nivelado del bloque EURO está escrito como `assert` en el informe de
`sorteo.py`, así que si un cambio lo rompe el script falla en vez de mentir:

| Subconjunto | Asientos | Objetivo |
|---|---|---|
| EURO total | 20 | 7 / 7 / 3 / 3 |
| Champions con rival conocido (`C1`–`C4`) | 8 | 3 / 3 / 1 / 1 |
| — de ellos nivel 2 (Inter, Leipzig) | 4 | 1 / 1 / 1 / 1 |
| — de ellos nivel 3 (PSV, LASK) | 4 | 2 / 2 / 0 / 0 |
| Teóricos y condicionales | 12 | 4 / 4 / 2 / 2 |

Orden: Pablo / Víctor / Jorge / Alberto. Los dos partidazos van a **uno por cabeza**,
igual que el Derbi y el Clásico en Liga.

## Verificación

`sorteo.py` y `hist2526.py` imprimen un resumen al ejecutarse. Comprueba siempre:

- Las entradas suman **57** en 26/27 y **53** en 25/26.
- Los cupos por bloque cuadran (`sorteo.py` lo asegura con `assert`).
- El informe **Nivelado del bloque EURO** sale todo en `OK` (también con `assert`).
- `hist2526.py` dice `¿coincide con el resumen del Excel? SÍ`.
- Abre `index.html` y prueba las dos pestañas y los filtros.

## Detalles de la página

- Dos pestañas: **2026/27** (por defecto) y **2025/26**. Enlace directo al
  histórico con `#2526`.
- Filtros por competición y por persona, independientes en cada temporada.
- Modo claro/oscuro; sigue al sistema y hay botón para forzarlo.
- Lleva `noindex, nofollow`: es pública pero no debe salir en buscadores.
- Los colores no son decorativos: los niveles usan una rampa ordinal de un solo
  tono y las competiciones una paleta categórica validada para daltonismo. Si
  añades colores, mantén ese criterio.

## Fuentes de los datos

- Calendario LaLiga 26/27: sorteo oficial del 30 jun 2026, publicado por
  [Realmadrid.com](https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/actualidad/el-calendario-del-real-madrid-para-la-liga-2026-27-30-06-2026).
- Fechas de Champions: [UEFA](https://www.uefa.com/uefachampionsleague/). Sorteo de
  la fase liga celebrado el **27 de agosto de 2026**; calendario con días y horas
  publicado por
  [Realmadrid.com](https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/actualidad/calendarios-del-real-madrid-en-la-primera-fase-de-la-champions-2026-27-29-08-2026)
  el 29 ago 2026. En el Bernabéu: Inter (8 sep), Leipzig (21 oct), PSV (24 nov) y
  LASK (19 ene). Fuera: Roma, AEK Atenas, Arsenal y Shakhtar.
- Fechas de Copa del Rey: [RFEF](https://rfef.es/es/noticias/la-temporada-202627-ya-tiene-establecidas-sus-fechas-clave).
- Temporada 25/26: Excel del sorteo del año pasado.
