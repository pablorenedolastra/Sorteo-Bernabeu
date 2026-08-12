# -*- coding: utf-8 -*-
"""Temporada 25/26 tal cual quedó en el Excel del sorteo del año pasado."""
import json
from collections import Counter

# ronda, fecha, sortkey, rival, nivel, hora, nota, asistentes, comp, bloque
H = [
 ("J1","Mar 19 ago 2025","2025-08-19","CA Osasuna",3,"21:00","Apertura temporada",["Alberto"],"LIGA"),
 ("J3","Sáb 30 ago 2025","2025-08-30","RCD Mallorca",3,"21:30","",["Alberto","Jorge"],"LIGA"),
 ("Fase Liga","Mar 16 sep 2025","2025-09-16","Olympique de Marsella",2,"21:00","Debut Champions",["Pablo","Víctor"],"CHAMPIONS"),
 ("J5","20/21 sep 2025","2025-09-20","RCD Espanyol",3,"","",["Pablo","Jorge"],"LIGA"),
 ("J8","4/5 oct 2025","2025-10-04","Villarreal CF",2,"","Fue Jorge · DEUDA",["Víctor","Alberto"],"LIGA"),
 ("Fase Liga","Mié 22 oct 2025","2025-10-22","Juventus",1,"21:00","PARTIDAZO 🔥",["Jorge","Víctor"],"CHAMPIONS"),
 ("J10","25/26 oct 2025","2025-10-25","FC Barcelona",1,"","EL CLÁSICO 🔥",["Pablo","Alberto"],"LIGA"),
 ("J11","1/2 nov 2025","2025-11-01","Valencia CF",2,"","",["Pablo","Víctor"],"LIGA"),
 ("J15","6/7 dic 2025","2025-12-06","RC Celta de Vigo",3,"","",["Pablo","Alberto"],"LIGA"),
 ("Fase Liga","Mié 10 dic 2025","2025-12-10","Manchester City",1,"21:00","PARTIDAZO 🔥",["Pablo","Víctor"],"CHAMPIONS"),
 ("J17","20/21 dic 2025","2025-12-20","Sevilla FC",2,"","Va Alberto para saldar deuda con Jorge",["Jorge","Víctor"],"LIGA"),
 ("J18","3/4 ene 2026","2026-01-03","Real Betis",2,"","",["Pablo","Jorge"],"LIGA"),
 ("J20","17/18 ene 2026","2026-01-17","CD Leganés",3,"","",["Víctor","Alberto"],"LIGA"),
 ("Fase Liga","Mar 20 ene 2026","2026-01-20","AS Monaco",2,"21:00","",["Pablo","Alberto"],"CHAMPIONS"),
 ("J22","31 ene / 1 feb 2026","2026-01-31","Rayo Vallecano",3,"","",["Pablo","Jorge"],"LIGA"),
 ("Dieciseisavos","Dom 1 feb 2026","2026-02-01","Benfica",2,"TBD","Teórico",["Víctor","Jorge"],"CHAMPIONS"),
 ("J24","14/15 feb 2026","2026-02-14","Real Sociedad",2,"","Pablo no pudo ir · fue Jorge",["Víctor","Jorge"],"LIGA"),
 ("J26","Lun 2 mar 2026","2026-03-02","Getafe CF",3,"","Cambiado Getafe y Girona por Atlético · Pablo recupera y debe a Víctor",["Pablo","Jorge"],"LIGA"),
 ("Octavos","Mié 11 mar 2026","2026-03-11","Manchester City",2,"TBD","Teórico",["Pablo","Alberto"],"CHAMPIONS"),
 ("J28","14/15 mar 2026","2026-03-14","CD Elche",3,"","",["Jorge","Víctor"],"LIGA"),
 ("J29","21/22 mar 2026","2026-03-21","Atlético de Madrid",1,"","DERBI 🔥 · Jorge no puede ir",["Víctor","Pablo"],"LIGA"),
 ("Cuartos","Mié 1 abr 2026","2026-04-01","Rival por determinar",1,"TBD","PARTIDAZO 🔥 · Teórico",["Víctor","Pablo"],"CHAMPIONS"),
 ("J31","11/12 abr 2026","2026-04-11","Girona FC",2,"","",["Jorge","Alberto"],"LIGA"),
 ("J33","21/22 abr 2026","2026-04-21","Deportivo Alavés",3,"","",["Pablo","Víctor"],"LIGA"),
 ("Semis","Vie 1 may 2026","2026-05-01","Rival por determinar",1,"TBD","PARTIDAZO 🔥 · Teórico",["Pablo","Víctor"],"CHAMPIONS"),
 ("J36","12/13 may 2026","2026-05-12","Real Oviedo",3,"","",["Víctor","Alberto"],"LIGA"),
 ("J38","23/24 may 2026","2026-05-23","Athletic Club",2,"","Final liga",["Pablo","Víctor"],"LIGA"),
]
H.sort(key=lambda x: x[2])

out = [dict(id=f"H{i}", comp=h[8], ronda=h[0], fecha=h[1], sort=h[2], rival=h[3], nivel=h[4],
            hora=h[5] or "—", nota=h[6], seats=len(h[7]),
            bloque="LIGA" if h[8] == "LIGA" else "EURO", asistentes=h[7])
       for i, h in enumerate(H)]
json.dump(out, open("hist2526.json", "w"), ensure_ascii=False, indent=1)

# comprobación contra el resumen que traía el Excel (Víctor 16, Pablo 17, Alberto 10, Jorge 10 = 53)
c = Counter(); lv = {p: Counter() for p in ["Pablo","Víctor","Jorge","Alberto"]}
for m in out:
    for p in m["asistentes"]:
        c[p] += 1; lv[p][m["nivel"]] += 1
print("partidos:", len(out), "| entradas:", sum(c.values()))
for p in ["Víctor","Pablo","Alberto","Jorge"]:
    print(f"  {p:8} N1={lv[p][1]} N2={lv[p][2]} N3={lv[p][3]}  total={c[p]}")
# el Excel decía Pablo 17 / Jorge 10, pero en la Real Sociedad fue Jorge, no Pablo
esperado = {"Víctor":(5,7,4,16), "Pablo":(5,6,5,16), "Alberto":(1,4,5,10), "Jorge":(1,5,5,11)}
ok = all((lv[p][1],lv[p][2],lv[p][3],c[p]) == e for p, e in esperado.items())
print("¿coincide con el resumen del Excel?", "SÍ" if ok else "NO")
if not ok:
    for p, e in esperado.items():
        got = (lv[p][1],lv[p][2],lv[p][3],c[p])
        if got != e: print("   dif", p, "excel", e, "calculado", got)
