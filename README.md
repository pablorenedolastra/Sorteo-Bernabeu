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
- **Bloque Champions + Copa** — se reparte solo por cuota total (`EURO_Q`), sin
  mirar niveles, porque hasta el sorteo de la fase liga no se sabe qué partidos
  son buenos. Todos los de Champions están puestos como **nivel 2 provisional**.

Los dos bloques no se mezclan: cambiar algo en Champions no debe descuadrar la Liga.

Restricciones adicionales, todas en la función `score()` de `sorteo.py`:

- Alberto va preferentemente con Pablo o con Jorge (máximo 2 veces con Víctor).
- El Derbi y el Clásico son los dos únicos nivel 1 garantizados: 4 asientos, uno
  por cabeza.
- Nadie tres partidos seguidos; sin sequías largas.
- Las parejas se acercan al reparto más variado posible (`PAIR_T`), que no es
  uniforme: como Pablo y Víctor van a 19 de 29 partidos, coinciden por fuerza un
  mínimo de 9 veces.
- La semifinal de Copa no repite exactamente la pareja del Derbi ni la del Clásico.

Casos particulares fijados a mano en `FIXED` (entran *antes* de optimizar, el
sorteo se construye respetándolos):

- `L3` — 30 ago, Málaga: solo hay **una entrada**, va Jorge.
- `L1` — 26 ago, Real Sociedad: Alberto + Víctor (Pablo no está).

## Cómo hacer un cambio

**Nunca edites `index.html`.** Según el tipo de cambio:

### Cambiar quién va a un partido de 2026/27

Añade una entrada a `POST` en `sorteo.py`, que se aplica *después* del sorteo:

```python
POST = {"L8": ["Víctor", "Jorge"]}   # Villarreal: entra Jorge en lugar de Pablo
```

Es una sustitución directa: **descuadra la cuota a propósito** y no se re-optimiza
nada, para no descolocar el resto del calendario. Si el cambio rompe un cupo de
forma relevante, dilo en las reglas de la página (`rules_html()` en `build.py`)
para que quien la lea entienda por qué no cuadra.

Alternativa: si quieres que el sorteo *respete* la restricción y reequilibre lo
demás, mete el partido en `FIXED` en vez de en `POST`. Ojo: eso vuelve a barajar
el resto de asignaciones.

### Corregir la temporada 2025/26

Edita la lista `H` en `hist2526.py` y actualiza el dict `esperado` del final, que
es la comprobación contra el resumen original del Excel.

### Reetiquetar los niveles de Champions (pendiente)

Cuando se conozcan los rivales, cambia el campo `nivel` de las filas `C1`–`C8` en
`sorteo.py`. Al estar en su propio bloque, la Liga no se ve afectada.

## Verificación

`sorteo.py` y `hist2526.py` imprimen un resumen al ejecutarse. Comprueba siempre:

- Las entradas suman **57** en 26/27 y **53** en 25/26.
- Los cupos por bloque cuadran (`sorteo.py` lo asegura con `assert`).
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
- Fechas de Champions: [UEFA](https://www.uefa.com/uefachampionsleague/).
  Sorteo de la fase liga: **27 de agosto de 2026**.
- Fechas de Copa del Rey: [RFEF](https://rfef.es/es/noticias/la-temporada-202627-ya-tiene-establecidas-sus-fechas-clave).
- Temporada 25/26: Excel del sorteo del año pasado.
