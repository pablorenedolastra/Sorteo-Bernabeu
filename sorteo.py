# -*- coding: utf-8 -*-
import random, json, itertools
from collections import Counter, defaultdict

# id, comp, ronda, fecha_txt, sortkey, rival, nivel, hora, nota, seats, bloque
M = [
 ("L1","LIGA","J1","Mié 26 ago 2026","2026-08-26","Real Sociedad",2,"21:00","Estreno en casa (jornada aplazada)",2,"LIGA"),
 ("L3","LIGA","J3","Dom 30 ago 2026","2026-08-30","Málaga CF",3,"17:00","⚠️ Solo 1 entrada disponible",1,"LIGA"),
 ("L5","LIGA","J5","12/13 sep 2026","2026-09-12","Rayo Vallecano",3,"TBD","",2,"LIGA"),
 ("C1","CHAMPIONS","Fase Liga (casa 1)","Sep/Oct 2026","2026-09-09","Rival por determinar",2,"21:00","Sorteo fase liga: 27 ago 2026",2,"EURO"),
 ("L8","LIGA","J8","10/11 oct 2026","2026-10-10","Villarreal CF",2,"TBD","",2,"LIGA"),
 ("L9","LIGA","J9","17/18 oct 2026","2026-10-17","Sevilla FC",2,"TBD","",2,"LIGA"),
 ("C2","CHAMPIONS","Fase Liga (casa 2)","Oct/Nov 2026","2026-10-20","Rival por determinar",2,"21:00","Sorteo fase liga: 27 ago 2026",2,"EURO"),
 ("L13","LIGA","J13","21/22 nov 2026","2026-11-21","RC Celta de Vigo",3,"TBD","",2,"LIGA"),
 ("C3","CHAMPIONS","Fase Liga (casa 3)","Nov/Dic 2026","2026-11-24","Rival por determinar",2,"21:00","Sorteo fase liga: 27 ago 2026",2,"EURO"),
 ("L14","LIGA","J14","28/29 nov 2026","2026-11-28","Deportivo Alavés",3,"TBD","",2,"LIGA"),
 ("L16","LIGA","J16","12/13 dic 2026","2026-12-12","CA Osasuna",3,"TBD","",2,"LIGA"),
 ("L18","LIGA","J18","2/3 ene 2027","2027-01-02","Getafe CF",3,"TBD","",2,"LIGA"),
 ("L19","LIGA","J19","9/10 ene 2027","2027-01-09","Levante UD",3,"TBD","",2,"LIGA"),
 ("K1","COPA","Cuartos de final","Mié 13 ene 2027","2027-01-13","Rival por determinar",2,"TBD","Teórico · solo si se juega en el Bernabéu",2,"EURO"),
 ("C4","CHAMPIONS","Fase Liga (casa 4)","Ene 2027","2027-01-19","Rival por determinar",2,"21:00","Sorteo fase liga: 27 ago 2026",2,"EURO"),
 ("L21","LIGA","J21","23/24 ene 2027","2027-01-23","Real Betis",2,"TBD","",2,"LIGA"),
 ("L24","LIGA","J24","13/14 feb 2027","2027-02-13","Athletic Club",2,"TBD","",2,"LIGA"),
 ("C5","CHAMPIONS","Play-off (vuelta)","23/24 feb 2027","2027-02-23","Rival por determinar",2,"21:00","Condicional · solo si el Madrid acaba 9º-24º",2,"EURO"),
 ("L26","LIGA","J26","27/28 feb 2027","2027-02-27","Valencia CF",2,"TBD","",2,"LIGA"),
 ("K2","COPA","Semifinal (vuelta)","Mié 3 mar 2027","2027-03-03","Rival por determinar",1,"TBD","Teórico",2,"EURO"),
 ("L28","LIGA","J28","13/14 mar 2027","2027-03-13","RCD Espanyol",3,"TBD","",2,"LIGA"),
 ("C6","CHAMPIONS","Octavos (vuelta)","16/17 mar 2027","2027-03-16","Rival por determinar",2,"21:00","Teórico",2,"EURO"),
 ("L30","LIGA","J30","3/4 abr 2027","2027-04-03","Atlético de Madrid",1,"TBD","DERBI 🔥",2,"LIGA"),
 ("C7","CHAMPIONS","Cuartos (una de las 2)","6/7 o 13/14 abr 2027","2027-04-13","Rival por determinar",2,"21:00","Teórico",2,"EURO"),
 ("L33","LIGA","J33","20/22 abr 2027","2027-04-20","Elche CF",3,"TBD","",2,"LIGA"),
 ("C8","CHAMPIONS","Semifinal (una de las 2)","27/28 abr o 4/5 may 2027","2027-05-04","Rival por determinar",2,"21:00","Teórico",2,"EURO"),
 ("L35","LIGA","J35","8/9 may 2027","2027-05-08","FC Barcelona",1,"TBD","EL CLÁSICO 🔥",2,"LIGA"),
 ("L36","LIGA","J36","15/16 may 2027","2027-05-15","Racing de Santander",3,"TBD","",2,"LIGA"),
 ("L38","LIGA","J38","29/30 may 2027","2027-05-29","RC Deportivo",3,"TBD","Última jornada",2,"LIGA"),
]
M.sort(key=lambda x: x[4])
BY = {m[0]: m for m in M}

PEOPLE = ["Pablo", "Víctor", "Jorge", "Alberto"]

# --- BLOQUE 1: LaLiga se equilibra por niveles consigo misma ---
LIGA_Q = {1: {"Pablo":1,"Víctor":1,"Jorge":1,"Alberto":1},     # 4 asientos (Derbi + Clásico)
          2: {"Pablo":4,"Víctor":4,"Jorge":2,"Alberto":2},     # 12 asientos
          3: {"Pablo":7,"Víctor":7,"Jorge":3,"Alberto":4}}     # 21 asientos
# --- BLOQUE 2: Champions + Copa, por cuota total (los niveles aún no son fiables) ---
EURO_Q = {"Pablo":7,"Víctor":7,"Jorge":3,"Alberto":3}          # 20 asientos

# asignaciones fijadas a mano
FIXED = {"L3": ["Jorge"], "L1": ["Alberto","Víctor"]}

# grupos: (clave, lista de partidos, cuota)
GROUPS = []
for lv in (1,2,3):
    GROUPS.append((("LIGA",lv), [m for m in M if m[10]=="LIGA" and m[6]==lv], LIGA_Q[lv]))
GROUPS.append((("EURO",0), [m for m in M if m[10]=="EURO"], EURO_Q))

for key, ms, q in GROUPS:
    s = sum(m[9] for m in ms)
    assert s == sum(q.values()), (key, s, sum(q.values()))
    print(f"{key}: {len(ms)} partidos, {s} asientos, cuota {q}")

def build(rng):
    assign = {}
    for key, ms, q in GROUPS:
        pool = []
        for p in PEOPLE: pool += [p]*q[p]
        fixed = {m[0]: FIXED[m[0]] for m in ms if m[0] in FIXED}
        for mid, who in fixed.items():
            for p in who: pool.remove(p)
        free = [m for m in ms if m[0] not in fixed]
        for _ in range(500):
            rng.shuffle(free)
            pk = list(pool); tmp = dict(fixed); ok = True
            for m in free:
                need = m[9]
                cnt = Counter(pk)
                cands = [p for p in PEOPLE if cnt[p] > 0]
                if len(cands) < need: ok = False; break
                top = cands[:]; rng.shuffle(top)
                pick = sorted(top, key=lambda p: -cnt[p])[:need]
                for p in pick: pk.remove(p)
                tmp[m[0]] = pick
            if ok and not pk:
                assign.update(tmp); break
        else:
            return None
    return assign

QTOT = {"Pablo":19,"Víctor":19,"Jorge":9,"Alberto":10}
# Objetivo de parejas: es el reparto más variado posible dado que (a) Pablo y Víctor
# van a 19 de 29 partidos, así que coinciden por fuerza al menos 9 veces, (b) Alberto
# solo puede ir 2 veces con Víctor y (c) Alberto y Jorge deben coincidir al menos 2.
PAIR_T = {("Pablo","Víctor"):12, ("Jorge","Pablo"):1, ("Alberto","Pablo"):6,
          ("Jorge","Víctor"):5, ("Alberto","Víctor"):2, ("Alberto","Jorge"):2}

def score(a):
    s = 0.0
    pairs = Counter(); av = 0
    for m in M:
        w = a[m[0]]
        if len(w) == 2:
            pairs[tuple(sorted(w))] += 1
            if set(w) == {"Alberto","Víctor"}: av += 1
    # 1) Alberto prefiere Pablo/Jorge (el J1 con Víctor ya está fijado por Pablo)
    s += max(0, av-2)*70 + av*7
    # 2) parejas cerca del reparto más variado posible
    for k, v in PAIR_T.items():
        s += (pairs.get(k,0) - v)**2 * 6.0
    # 3) sin tres partidos seguidos
    seq = [set(a[m[0]]) for m in M]
    for i in range(len(seq)-2):
        for p in PEOPLE:
            if p in seq[i] and p in seq[i+1] and p in seq[i+2]: s += 9
    # 4) sin sequías largas
    for p in PEOPLE:
        idx = [i for i,x in enumerate(seq) if p in x]
        lim = 4 if p in ("Pablo","Víctor") else 7
        s += sum((b-aa-lim)**2 for aa,b in zip(idx, idx[1:]) if b-aa > lim)*1.5
    # 5) los teóricos (Copa + eliminatorias CH) repartidos en proporción
    teo = [m for m in M if "Teórico" in m[8] or "Condicional" in m[8]]
    c = Counter()
    for m in teo:
        for p in a[m[0]]: c[p]+=1
    for p, t in {"Pablo":4,"Víctor":4,"Jorge":2,"Alberto":2}.items():
        s += (c[p]-t)**2 * 2.0
    # 6) la semifinal de Copa no repite exactamente la pareja del Derbi ni la del Clásico
    if set(a["K2"]) in (set(a["L30"]), set(a["L35"])): s += 45
    return s

best, bs = None, 1e18
rng = random.Random(20262027)
for _ in range(9000):
    a = build(rng)
    if a is None: continue
    sc = score(a)
    if sc < bs: bs, best = sc, a
assign = best
print("\nMejor score:", round(bs,2))

# Cambios pedidos a mano DESPUÉS del sorteo. Son sustituciones directas: alteran la
# cuota a propósito, así que no se re-optimiza nada para no descolocar el resto.
POST = {"L8": ["Víctor", "Jorge"]}   # Villarreal: entra Jorge en lugar de Pablo
for mid, who in POST.items():
    if assign[mid] != who:
        print(f"  cambio manual {mid}: {' + '.join(assign[mid])} -> {' + '.join(who)}")
        assign[mid] = who

# ---- informe ----
tot = Counter(); liga = defaultdict(Counter); euro = Counter(); pairs = Counter()
for m in M:
    for p in assign[m[0]]:
        tot[p] += 1
        if m[10] == "LIGA": liga[p][m[6]] += 1
        else: euro[p] += 1
    if len(assign[m[0]]) == 2: pairs[tuple(sorted(assign[m[0]]))] += 1
T = sum(tot.values())
print(f"\nTotal asientos: {T}")
for p in PEOPLE:
    print(f"{p:8} Liga: N1={liga[p][1]} N2={liga[p][2]} N3={liga[p][3]} (={sum(liga[p].values())})"
          f"  CH+Copa={euro[p]}  TOTAL={tot[p]:3} {tot[p]/T*100:5.1f}%")
print("\nParejas:", dict(pairs))
print("\nCalendario:")
for m in M:
    print(f"{m[4]}  {m[10]:4} {m[1][:4]:4} {m[2][:24]:24} {m[5][:22]:22} N{m[6]}  {' + '.join(assign[m[0]])}")

json.dump([dict(id=m[0], comp=m[1], ronda=m[2], fecha=m[3], sort=m[4], rival=m[5], nivel=m[6],
                hora=m[7], nota=m[8], seats=m[9], bloque=m[10], asistentes=assign[m[0]])
           for m in M], open("sorteo.json","w"), ensure_ascii=False, indent=1)
