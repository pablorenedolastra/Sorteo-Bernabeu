# Sorteo Bernabéu

Web de consulta del reparto de los dos abonos del Bernabéu entre **Pablo, Víctor,
Jorge y Alberto**. Publicada en GitHub Pages:

**https://pablorenedolastra.github.io/Sorteo-Bernabeu/**

> `index.html` es un **fichero generado**. No lo edites a mano: los totales, los
> porcentajes, la matriz de parejas y varias frases de las reglas se calculan a
> partir de los datos. Si lo tocas directamente, la página empieza a mentir.

## Cómo está montado

Las fechas y horas **se actualizan solas cada noche**. Un workflow de GitHub
Actions pregunta a [football-data.org](https://www.football-data.org/) cuándo se
juega cada partido, actualiza `calendario.json`, regenera `index.html` y lo
commitea si algo ha cambiado. Todo Python sin dependencias externas, solo la
librería estándar.

Los datos viven en tres ficheros, con un dueño claro cada uno:

| Fichero | Qué es | Quién lo cambia |
|---|---|---|
| `calendario.json` | Los 29 partidos: fecha, hora, rival, nivel, asientos. | el cron, cada noche |
| `reparto.json` | Quién va a cada partido, con `POST` ya aplicado. | `sorteo.py`, una vez por temporada |
| `hist2526.json` | La temporada 2025/26, que ya es historia. | nadie |

Y los scripts:

| Script | Qué hace |
|---|---|
| `sorteo.py` | Celebra el sorteo. Escribe `reparto.json`. Se lanza **a mano**. |
| `actualizar_calendario.py` | Pide las fechas a la API y actualiza `calendario.json`. Lo lanza el cron. |
| `hist2526.py` | Datos de 2025/26. Escribe `hist2526.json`. |
| `build.py` | Cruza los tres JSON y genera `index.html`. |
| `test_actualizar.py` | Los tests. `python3 test_actualizar.py`, sin dependencias. |

```bash
python3 actualizar_calendario.py --dry-run   # qué cambiaría, sin tocar nada
python3 actualizar_calendario.py             # actualizar el calendario
python3 build.py                             # regenerar index.html
```

Hace falta una key gratuita de football-data.org en la variable
`FOOTBALL_DATA_TOKEN` (en GitHub ya está como secret del repo). La página sigue
siendo autocontenida: todo el CSS y el JS van inline, no carga nada de fuera y
funciona abriéndola en local.

### Por qué el calendario y el reparto están separados

Porque las fechas son una **entrada** del sorteo, no un adorno. `sorteo.py`
ordena los partidos por fecha (`M.sort`) y las reglas 3 y 4 de `score()` —"nadie
tres partidos seguidos", "sin sequías largas"— se evalúan sobre ese orden. Si un
proceso automático cambiara una fecha y volviera a lanzar el sorteo, el reparto
podría salir distinto: otro Derbi, otro Clásico, otras parejas.

Por eso el fichero que toca el cron, `calendario.json`, **no contiene
asistentes**. No tiene forma de alterar el reparto, y `sorteo.py` no se ejecuta
nunca de forma automática.

### Las dos reglas del actualizador

**Solo escribe fechas que la API da por finalizadas** (`status: TIMED`). Esto no
es prudencia teórica: los partidos que la API aún no ha fijado los devuelve con
la hora a las `00:00Z`, que en Madrid son las 01:00 o las 02:00. El día que se
montó esto, 31 de los 46 partidos estaban así. Escribirlos habría anunciado el
Villarreal a las dos de la madrugada de un domingo. Un rango escrito a mano como
"12/13 sep 2026" es mejor información que eso.

Si la API mueve una jornada fuera del rango escrito, no sobreescribe nada, pero
lo avisa en el mensaje del commit. Es la pista temprana de que LaLiga ha
recolocado la jornada.

**Rellenar el rival de una eliminatoria no cambia su nivel.** Cuando se conoce el
rival, renivelar el bloque sigue siendo una decisión que se toma a mano en
`POST`, como se hizo con Inter, Leipzig, PSV y LASK. El cron pone la etiqueta y
nada más.

Ante cualquier respuesta rara de la API —un error, un corte de red, o menos
partidos de los esperados— el script **aborta sin escribir**. Una fecha
desactualizada es mejor que una inventada, y mucho mejor que un `index.html`
roto.

### Lo que sigue siendo manual

- **La Copa del Rey** (`K1`, `K2`): el plan gratuito de la API no la cubre.
- **Los niveles** de los partidos, y renivelar un bloque cuando se conoce un rival.
- **El sorteo entero**, claro.

### Antes de la temporada que viene

Nada de esto se actualiza solo, así que conviene tenerlo junto:

1. **Sube `TEMPORADA`** en `actualizar_calendario.py` (ahora `2026`). Si no, la
   API devuelve la temporada vieja, el script ve menos partidos de los que
   espera y aborta sin escribir. Falla en seguro, pero falla en silencio: nadie
   se entera salvo que mire el correo de GitHub.
2. **Rehaz el sorteo**: borra `calendario.json`, actualiza la tabla `M` de
   `sorteo.py` con el calendario nuevo y lánzalo. Escribirá `reparto.json` y un
   `calendario.json` en blanco.
3. **Vuelve a sacar los ids**: `python3 actualizar_calendario.py --descubrir-ids`
   y rellena los `api_team`. Cambian con los ascensos y descensos.
4. **Reactiva el workflow** si GitHub lo ha desactivado. Lo hace tras 60 días sin
   actividad en el repo, y entre junio y agosto no hay partidos que actualizar,
   así que pasará casi todos los veranos. Avisa por correo y se reactiva con un
   clic desde la pestaña Actions.

El comentario de `ID_MADRID` dice contra qué se verificó y cuándo. Los ids de
equipo de football-data.org son estables, pero no cuesta nada comprobarlo.

### Si lo ejecutas en un Mac

Si `actualizar_calendario.py` falla con `CERTIFICATE_VERIFY_FAILED`, es que el
Python del instalador de python.org no tiene los certificados instalados. Se
arregla una sola vez:

```bash
open "/Applications/Python 3.13/Install Certificates.command"
```

O, como parche puntual, `SSL_CERT_FILE=/etc/ssl/cert.pem` delante del comando.
En GitHub Actions no pasa: el runner de Ubuntu trae su almacén configurado.

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
  Víctor. El reequilibrio de Osasuna/Levante lo subió a 3, y el intercambio
  Inter/Leipzig lo dejó en **4**, el doble del original. Eso ya no lo cumple
  `score()`: es una decisión tomada a mano en `POST`, a petición de Pablo y
  sabiendo el efecto. El informe de `sorteo.py` avisa con un ⚠️ cuando pasa de 3,
  para que no se cuele sin querer.
- El Derbi y el Clásico son los dos únicos nivel 1 garantizados: 4 asientos, uno
  por cabeza.
- Nadie tres partidos seguidos; sin sequías largas. Ojo: son penalizaciones que el
  optimizador minimiza, no prohibiciones. Pablo y Víctor van a 18 y 19 de los 29
  partidos, así que encadenar tres es casi inevitable: el sorteo lo dejó en 9 veces
  y los cambios de `POST` lo han llevado a **11**. Es esperable, porque los cambios
  de `POST` se aplican *después* de optimizar y no vuelven a mirar esta regla. Si
  algún día crece de más, la salida a mano no es reoptimizar (la temporada está
  empezada) sino buscar un intercambio que la baje.
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
        "C4":  ["Víctor", "Pablo"],     # intercambio: Pablo entra por Jorge (nivelado)
        "C2":  ["Víctor", "Alberto"],   # intercambio: Alberto y Jorge se cambian ...
        "C1":  ["Jorge", "Pablo"]}      #              ... el sitio entre Inter y Leipzig
```

- **Sustitución directa** — alguien entra en el sitio de otro. **Descuadra la cuota
  a propósito.** Es el caso del Villarreal (`L8`).
- **Intercambio** — dos personas se cambian el sitio entre dos partidos *del mismo
  bloque*. **No mueve ningún total**, solo cambia con quién va cada uno. Si además
  los dos partidos son del mismo nivel, tampoco mueve ninguna cuota: es el caso de
  Osasuna/Levante (`L16` y `L19`), el reequilibrio entre Alberto y Jorge. Si son de
  niveles distintos *dentro del bloque EURO* tampoco pasa nada, porque ese bloque se
  reparte por cuota total y no por niveles: es el caso de Leipzig/LASK (`C4`), el
  nivelado de Champions. Lo que **no** vale es cruzar dos partidos de Liga de
  niveles distintos, porque ahí la cuota sí es por nivel.

  Encima del nivelado hay un segundo intercambio, Inter/Leipzig (`C1` y `C2`), que
  pidió Pablo: Alberto y Jorge se cambian el sitio, con Jorge al Inter y Alberto al
  Leipzig. Mismo bloque y mismo nivel, así que no mueve ni cuotas ni el nivelado —
  los dos partidazos siguen a uno por cabeza. Lo que sí mueve son las parejas, y
  **sube Alberto+Víctor de 3 a 4**, rompiendo el tope. Está aceptado a conciencia
  y anotado en el comentario de `POST`; a cambio Pablo queda casi equilibrado entre
  Jorge (3) y Alberto (4).

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
