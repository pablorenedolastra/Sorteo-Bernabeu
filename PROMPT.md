Trabajas en el repo `pablorenedolastra/Sorteo-Bernabeu`, que publica por GitHub
Pages la web del sorteo de los dos abonos del Bernabéu que compartimos Pablo,
Víctor, Jorge y Alberto: https://pablorenedolastra.github.io/Sorteo-Bernabeu/

Antes de tocar nada, lee el `README.md` del repo: explica el modelo del sorteo
(dos bloques independientes, cuotas por nivel en Liga, cuota total en
Champions+Copa) y cómo se hace cada tipo de cambio. Lee también `sorteo.py`
entero, sobre todo `LIGA_Q`, `EURO_Q`, `FIXED`, `POST` y la función `score()`.

Regla que no se salta nunca: **`index.html` es un fichero generado, no se edita a
mano.** Los totales, los porcentajes, la matriz de parejas y varias frases de las
reglas se calculan a partir de los datos. Todo cambio se hace en los `.py` y se
regenera con:

    python3 sorteo.py && python3 hist2526.py && python3 build.py

Flujo para cada cambio que te pida:

1. Localiza dónde va: sustituir a alguien en un partido de 26/27 → una entrada en
   `POST` de `sorteo.py`; corregir la temporada pasada → la lista `H` de
   `hist2526.py` (y actualiza el dict `esperado` del final); reetiquetar niveles
   de Champions → el campo `nivel` de las filas `C1`–`C8`.
2. Regenera y **lee la salida de los scripts**: las entradas tienen que sumar 57
   en 26/27 y 53 en 25/26, y `hist2526.py` debe decir
   `¿coincide con el resumen del Excel? SÍ`.
3. Si el cambio descuadra una cuota, no lo escondas: dilo en la respuesta y déjalo
   escrito en el comentario de `POST`, igual que está hecho con el Villarreal. La
   página ya no publica las reglas del sorteo, es material interno.
   Antes de cambiar `PAIR_T` lee su comentario: los seis números están atados por
   cuatro ecuaciones y tocarlos reoptimiza el calendario entero. Para mover parejas
   sin descolocar nada, usa un intercambio en `POST` (dos partidos del mismo bloque
   y nivel), como el de Osasuna/Levante.
4. Abre `index.html` y comprueba de verdad que se ve bien: las dos pestañas
   (2026/27 por defecto, 2025/26 en la segunda), los filtros por competición y
   por persona en cada temporada, y que no hay errores en la consola.
5. Commit con un mensaje que diga qué cambió y qué efecto tuvo en el reparto, y
   push a `main`. Pages se actualiza solo en un par de minutos.

Contexto sobre el sorteo que conviene que tengas presente al proponer cosas:

- Pablo y Víctor pagaron 1/3 cada uno; Jorge y Alberto, 1/6. Ese es el criterio
  de reparto y cualquier desviación hay que justificarla.
- LaLiga se equilibra por niveles consigo misma. Champions y Copa van en bloque
  aparte y **no deben afectar al equilibrio de la Liga**.
- Los partidos de Champions están todos como nivel 2 provisional. El sorteo de la
  fase liga es el **27 de agosto de 2026**; cuando se sepan los rivales hay que
  reetiquetar niveles y reequilibrar solo ese bloque.
- Alberto prefiere ir con Pablo o con Jorge.
- El 30 de agosto (Málaga) solo hay una entrada.

Si algo del encargo choca con estas reglas, dímelo antes de aplicarlo en vez de
resolverlo por tu cuenta.

Primera tarea: confirma que el repo está en el estado correcto —el `index.html`
del repo debe coincidir con el que generan los scripts—, y si no coincide,
regenéralo y súbelo. Luego te paso los cambios que quiero.
