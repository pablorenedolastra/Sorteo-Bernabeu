# -*- coding: utf-8 -*-
import json
from collections import Counter, defaultdict

PEOPLE = ["Pablo", "Víctor", "Jorge", "Alberto"]
SHARE = {"Pablo": "1/3", "Víctor": "1/3", "Jorge": "1/6", "Alberto": "1/6"}
SHAREV = {"Pablo": 1/3, "Víctor": 1/3, "Jorge": 1/6, "Alberto": 1/6}
MES = {"01":"Enero","02":"Febrero","03":"Marzo","04":"Abril","05":"Mayo","06":"Junio",
       "07":"Julio","08":"Agosto","09":"Septiembre","10":"Octubre","11":"Noviembre","12":"Diciembre"}
COMPLBL = {"LIGA":"LaLiga", "CHAMPIONS":"Champions", "COPA":"Copa del Rey"}
NIVLBL = {1:"Partidazo", 2:"Medio", 3:"Normal"}

def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def stats(D):
    tot = Counter(); liga = defaultdict(Counter); euro = defaultdict(Counter)
    pairs = Counter(); bycomp = Counter(); seats = Counter()
    for m in D:
        bycomp[m["comp"]] += 1
        seats[m["bloque"]] += m["seats"]
        for p in m["asistentes"]:
            tot[p] += 1
            (liga if m["bloque"] == "LIGA" else euro)[p][m["nivel"]] += 1
        if len(m["asistentes"]) == 2:
            pairs[tuple(sorted(m["asistentes"]))] += 1
    return tot, liga, euro, pairs, bycomp, seats

def bar(counts, width_pct):
    segs = "".join(f'<span class="seg s{lv}" style="flex:{counts[lv]}"><b>{counts[lv]}</b></span>'
                   for lv in (1,2,3) if counts[lv])
    return f'<div class="bar" style="width:{width_pct:.1f}%">{segs}</div>'

def season_html(key, D, prov):
    tot, liga, euro, pairs, bycomp, seats = stats(D)
    T = sum(tot.values())
    maxliga = max(sum(liga[p].values()) for p in PEOPLE) or 1
    maxeuro = max(sum(euro[p].values()) for p in PEOPLE) or 1

    # calendario
    rows = []; last = None
    for m in D:
        ym = m["sort"][:7]
        if ym != last:
            last = ym
            rows.append(f'<tr class="mrow"><th colspan="6" scope="colgroup">{MES[ym[5:7]]} {ym[:4]}</th></tr>')
        chips = "".join(f'<span class="who">{esc(p)}</span>' for p in m["asistentes"])
        if m["seats"] == 1: chips += '<span class="who ghost">— libre —</span>'
        nota = f'<div class="nota">{esc(m["nota"])}</div>' if m["nota"] else ""
        nivsub = "Provisional" if (prov and m["bloque"] == "EURO") else NIVLBL[m["nivel"]]
        tbd = " tbd" if ("Teórico" in m["nota"] or "Condicional" in m["nota"]) else ""
        rows.append(
            f'<tr data-comp="{m["comp"]}" data-who="{esc("|".join(m["asistentes"]))}" class="mtch{tbd}">'
            f'<td class="c-date"><span class="d">{esc(m["fecha"])}</span><span class="h">{esc(m["hora"])}</span></td>'
            f'<td class="c-comp"><span class="badge b-{m["comp"].lower()}">{COMPLBL[m["comp"]]}</span>'
            f'<span class="ronda">{esc(m["ronda"])}</span></td>'
            f'<td class="c-rival">{esc(m["rival"])}{nota}</td>'
            f'<td class="c-niv"><span class="niv n{m["nivel"]}">N{m["nivel"]}</span>'
            f'<span class="nivt">{nivsub}</span></td>'
            f'<td class="c-who">{chips}</td><td class="c-seats">{m["seats"]}</td></tr>')

    # tarjetas
    eurolbl = "Champions + Copa" if prov else "Champions"
    cards = []
    for p in PEOPLE:
        lt, et = sum(liga[p].values()), sum(euro[p].values())
        diff = tot[p] - SHAREV[p]*T
        dtxt = "±0" if abs(diff) < 0.25 else (f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}")
        cards.append(f"""      <div class="pcard">
        <div class="phead"><span class="pname">{esc(p)}</span><span class="pquota">paga {SHARE[p]}</span></div>
        <div class="pnum"><b>{tot[p]}</b><span>entradas · {tot[p]/T*100:.1f}%</span>
          <span class="delta">{dtxt} vs cuota</span></div>
        <div class="blk"><span class="blkl">LaLiga <b>{lt}</b></span>{bar(liga[p], lt/maxliga*100)}</div>
        <div class="blk sep"><span class="blkl">{eurolbl} <b>{et}</b>{' <i>· nivel provisional</i>' if prov else ''}</span>
          {bar(euro[p], et/maxeuro*100)}</div>
      </div>""")

    # tabla resumen
    trows = ""
    for p in PEOPLE:
        lt, et = sum(liga[p].values()), sum(euro[p].values())
        trows += (f'<tr><th scope="row">{esc(p)}</th><td>{SHARE[p]}</td>'
                  f'<td>{liga[p][1]}</td><td>{liga[p][2]}</td><td>{liga[p][3]}</td><td><b>{lt}</b></td>'
                  f'<td>{et}</td><td><b>{tot[p]}</b></td>'
                  f'<td>{tot[p]/T*100:.1f}%</td><td>{SHAREV[p]*100:.1f}%</td></tr>')
    trows += (f'<tr class="ttot"><th scope="row">TOTAL</th><td>1</td>'
              f'<td>{sum(liga[p][1] for p in PEOPLE)}</td><td>{sum(liga[p][2] for p in PEOPLE)}</td>'
              f'<td>{sum(liga[p][3] for p in PEOPLE)}</td><td><b>{seats["LIGA"]}</b></td>'
              f'<td>{seats["EURO"]}</td><td><b>{T}</b></td><td>100%</td><td>100%</td></tr>')

    mrows = ""
    for a in PEOPLE:
        cells = "".join('<td class="dash">—</td>' if a == b else
                        (lambda v: f'<td{" class=hi" if v >= 6 else ""}>{v}</td>')(pairs.get(tuple(sorted((a,b))), 0))
                        for b in PEOPLE)
        mrows += f'<tr><th scope="row">{esc(a)}</th>{cells}</tr>'

    comps = [c for c in ("LIGA","CHAMPIONS","COPA") if bycomp[c]]
    fcomp = "".join(f'<button class="fb" data-comp="{c}">{COMPLBL[c]}</button>' for c in comps)
    fwho = "".join(f'<button class="fb" data-who="{esc(p)}">{esc(p)}</button>' for p in PEOPLE)
    tiles = "".join(f'<div class="tile"><b>{bycomp[c]}</b><span>de {COMPLBL[c]}</span></div>' for c in comps)

    if prov:
        sub = ("LaLiga se equilibra por niveles consigo misma. Champions y Copa van en bloque "
               "aparte, repartidos solo por cuota, porque hasta el sorteo del 27 de agosto no se "
               "sabe qué partidos son buenos.")
    else:
        sub = ("Temporada cerrada. Así quedó el sorteo, con las notas de deudas e intercambios "
               "tal y como se apuntaron en su momento.")

    return f"""<div class="season" id="s{key}" {'hidden' if not prov else ''}>
<section>
  <h2>Resumen</h2>
  <div class="tiles">
    <div class="tile"><b>{len(D)}</b><span>partidos en el Bernabéu</span></div>
    <div class="tile"><b>{T}</b><span>entradas repartidas</span></div>
    {tiles}
  </div>
</section>
<section>
  <h2>Reparto por persona</h2>
  <p class="h2sub">{sub}</p>
  <div class="grid2">
{chr(10).join(cards)}
  </div>
  <div class="legend"><span><i class="sw s1"></i>Nivel 1 · partidazo</span>
    <span><i class="sw s2"></i>Nivel 2 · medio</span>
    <span><i class="sw s3"></i>Nivel 3 · normal</span></div>
</section>
<section>
  <h2>Calendario</h2>
  <div class="filters flt">
    <button class="fb on" data-comp="ALL">Todos</button>{fcomp}
    <span class="fsep"></span>{fwho}
  </div>
  <table class="cal">
    <thead><tr><th>Fecha</th><th>Competición</th><th>Rival</th><th>Nivel</th>
    <th>Quién va</th><th class="th-seats">Ent.</th></tr></thead>
    <tbody>
{chr(10).join(rows)}
    </tbody>
  </table>
  <div class="empty">Ningún partido con ese filtro.</div>
</section>
<section>
  <h2>Tabla resumen</h2>
  <table class="sum">
    <thead><tr><th>Persona</th><th>Paga</th><th>Liga N1</th><th>Liga N2</th><th>Liga N3</th>
    <th>Liga total</th><th>{eurolbl}</th><th>Total</th><th>% real</th><th>% objetivo</th></tr></thead>
    <tbody>{trows}</tbody>
  </table>
</section>
<section>
  <h2>Con quién te tocó ir</h2>
  <table class="matrix">
    <thead><tr><th></th>{"".join(f"<th>{esc(p)}</th>" for p in PEOPLE)}</tr></thead>
    <tbody>{mrows}</tbody>
  </table>
</section>
{"" if prov else historia_html(D, tot, liga, euro, T)}
</div>"""

def historia_html(D, tot, liga, euro, T):
    pc = lambda p: f"{tot[p]/T*100:.1f}%".replace(".", ",")
    n1 = {p: liga[p][1] + euro[p][1] for p in PEOPLE}
    n1tot = sum(n1.values())
    nliga = sum(1 for m in D if m["bloque"] == "LIGA")
    nch = len(D) - nliga
    return f"""<section>
  <h2>Cómo fue aquel sorteo</h2>
  <div class="rules"><ul>
    <li><b>Los que menos pagaban acabaron por encima de su cuota.</b> Pablo y Víctor cerraron en
      {pc('Pablo')} y {pc('Víctor')} frente al 33,3% que les tocaba, y Jorge y Alberto en
      {pc('Jorge')} y {pc('Alberto')} frente al 16,7%. Cerca, pero el reparto no se hizo cuota a cuota.</li>
    <li><b>Los partidazos sí quedaron desiguales.</b> De los {n1tot} asientos de nivel 1, Pablo y
      Víctor se llevaron {n1['Pablo']} cada uno y a Jorge y Alberto les tocó {n1['Jorge']}. Ese es
      justo el desequilibrio que el sorteo de este año corrige aplicando la cuota dentro de cada nivel.</li>
    <li><b>Hubo deudas e intercambios sobre la marcha</b> (Villarreal, Sevilla, Real Sociedad,
      Getafe). Están anotados bajo el rival para no perder el rastro.</li>
    <li><b>{nliga} partidos de Liga y {nch} de Champions</b>, {T} entradas en total. El 19 de agosto
      contra Osasuna solo hubo una entrada, igual que pasa este año el 30 de agosto.</li>
  </ul></div>
</section>"""

D27 = json.load(open("sorteo.json"))
D26 = json.load(open("hist2526.json"))

HTML = f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="Sorteo de los abonos del Bernabéu.">
<title>Sorteo Bernabéu · Pablo, Víctor, Jorge y Alberto</title>
<style>
:root{{color-scheme:light;
  --bg:#f4f4f1;--surface:#fcfcfb;--line:#e2e1dc;--line2:#eeede9;
  --ink:#0b0b0b;--ink2:#52514e;--ink3:#83817a;
  --s1:#104281;--s2:#2a78d6;--s3:#86b6ef;
  --c-liga:#2a78d6;--c-champions:#eb6834;--c-copa:#1baf7a;--accent:#104281;}}
@media (prefers-color-scheme:dark){{:root:where(:not([data-theme="light"])){{color-scheme:dark;
  --bg:#111110;--surface:#1a1a19;--line:#33332f;--line2:#262624;
  --ink:#fff;--ink2:#c3c2b7;--ink3:#8f8e85;
  --s1:#184f95;--s2:#3987e5;--s3:#9ec5f4;
  --c-liga:#3987e5;--c-champions:#d95926;--c-copa:#199e70;--accent:#9ec5f4;}}}}
:root[data-theme="dark"]{{color-scheme:dark;
  --bg:#111110;--surface:#1a1a19;--line:#33332f;--line2:#262624;
  --ink:#fff;--ink2:#c3c2b7;--ink3:#8f8e85;
  --s1:#184f95;--s2:#3987e5;--s3:#9ec5f4;
  --c-liga:#3987e5;--c-champions:#d95926;--c-copa:#199e70;--accent:#9ec5f4;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 -webkit-font-smoothing:antialiased}}
.wrap{{max-width:1080px;margin:0 auto;padding:28px 18px 72px}}
header.top{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:18px}}
h1{{font-size:28px;line-height:1.15;margin:0 0 6px;letter-spacing:-.02em}}
h1 span{{color:var(--ink3);font-weight:600}}
.sub{{color:var(--ink2);font-size:14px;margin:0;max-width:62ch}}
#tt{{background:var(--surface);border:1px solid var(--line);color:var(--ink2);border-radius:999px;
 padding:7px 14px;font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}}
#tt:hover{{border-color:var(--ink3)}}
.tabs{{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:4px}}
.tab{{background:none;border:0;border-bottom:2px solid transparent;color:var(--ink3);
 font:inherit;font-weight:600;font-size:14.5px;padding:9px 4px;margin-right:18px;cursor:pointer}}
.tab:hover{{color:var(--ink2)}}
.tab[aria-selected="true"]{{color:var(--ink);border-bottom-color:var(--accent)}}
.tab .tg{{display:inline-block;margin-left:7px;font-size:10.5px;font-weight:700;letter-spacing:.05em;
 text-transform:uppercase;padding:2px 7px;border-radius:999px;background:var(--line);color:var(--ink2);
 vertical-align:1px}}
.tab[aria-selected="true"] .tg{{background:var(--accent);color:var(--surface)}}
section{{margin-top:32px}}
h2{{font-size:13px;text-transform:uppercase;letter-spacing:.09em;color:var(--ink3);margin:0 0 6px;font-weight:700}}
.h2sub{{color:var(--ink2);font-size:13.5px;margin:0 0 14px;max-width:70ch}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.tile{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:15px 16px}}
.tile b{{display:block;font-size:30px;line-height:1.05;letter-spacing:-.03em;font-variant-numeric:tabular-nums}}
.tile span{{color:var(--ink2);font-size:13px}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}
.pcard{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px}}
.phead{{display:flex;justify-content:space-between;align-items:baseline;gap:8px}}
.pname{{font-weight:700;font-size:17px}} .pquota{{font-size:12px;color:var(--ink3)}}
.pnum{{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin:8px 0 14px}}
.pnum b{{font-size:28px;letter-spacing:-.03em;font-variant-numeric:tabular-nums}}
.pnum span{{font-size:13px;color:var(--ink2)}}
.delta{{font-size:11.5px;padding:2px 8px;border-radius:999px;border:1px solid var(--line);
 color:var(--ink2);font-variant-numeric:tabular-nums}}
.blk.sep{{margin-top:14px;padding-top:13px;border-top:1px solid var(--line2)}}
.blkl{{display:block;font-size:12px;color:var(--ink2);margin-bottom:6px}}
.blkl b{{color:var(--ink);font-variant-numeric:tabular-nums}}
.blkl i{{color:var(--ink3);font-style:normal}}
.bar{{display:flex;gap:2px;height:24px;min-width:30%}}
.seg{{display:flex;align-items:center;justify-content:center;min-width:20px;border-radius:2px;
 font-size:12px;font-weight:700;font-variant-numeric:tabular-nums}}
.seg:first-child{{border-radius:4px 2px 2px 4px}} .seg:last-child{{border-radius:2px 4px 4px 2px}}
.seg.s1{{background:var(--s1);color:#fff}} .seg.s2{{background:var(--s2);color:#fff}}
.seg.s3{{background:var(--s3);color:#0b0b0b}}
.legend{{display:flex;flex-wrap:wrap;gap:18px;margin-top:12px;font-size:12.5px;color:var(--ink2)}}
.legend span{{display:inline-flex;align-items:center;gap:7px}}
i.sw{{width:11px;height:11px;border-radius:3px;display:inline-block}}
i.sw.s1{{background:var(--s1)}} i.sw.s2{{background:var(--s2)}} i.sw.s3{{background:var(--s3)}}
table{{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--line);
 border-radius:12px;overflow:hidden;font-size:14px}}
th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line2);vertical-align:top}}
thead th{{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink3);
 background:var(--bg);font-weight:700;white-space:nowrap}}
tbody tr:last-child td,tbody tr:last-child th{{border-bottom:0}}
.sum td{{font-variant-numeric:tabular-nums}}
.ttot th,.ttot td{{font-weight:700;background:var(--bg)}}
.mrow th{{background:var(--bg);font-size:11.5px;text-transform:uppercase;letter-spacing:.09em;
 color:var(--ink3);font-weight:700;padding:9px 12px}}
.c-date{{white-space:nowrap;width:1%}}
.c-date .d{{display:block;font-weight:600}} .c-date .h{{display:block;color:var(--ink3);font-size:12px}}
.c-comp{{white-space:nowrap;width:1%}}
.badge{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;color:#fff}}
.b-liga{{background:var(--c-liga)}} .b-champions{{background:var(--c-champions)}} .b-copa{{background:var(--c-copa)}}
.ronda{{display:block;color:var(--ink3);font-size:12px;margin-top:3px}}
.c-rival{{font-weight:600}}
.nota{{font-weight:400;color:var(--ink3);font-size:12px;margin-top:3px;max-width:34ch}}
.c-niv{{white-space:nowrap;width:1%}}
.niv{{display:inline-block;width:26px;text-align:center;padding:2px 0;border-radius:4px;font-size:11px;font-weight:700}}
.niv.n1{{background:var(--s1);color:#fff}} .niv.n2{{background:var(--s2);color:#fff}}
.niv.n3{{background:var(--s3);color:#0b0b0b}}
.nivt{{display:block;color:var(--ink3);font-size:11.5px;margin-top:3px}}
.c-who{{width:1%;white-space:nowrap}}
.who{{display:inline-block;padding:3px 9px;border:1px solid var(--line);border-radius:999px;
 font-size:13px;font-weight:600;margin:1px 3px 1px 0;background:var(--bg)}}
.who.ghost{{color:var(--ink3);font-weight:400;font-style:italic;border-style:dashed}}
.c-seats{{width:1%;text-align:center;color:var(--ink3)}}
tr.tbd .c-rival,tr.tbd .c-date{{opacity:.8}}
.filters{{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:12px}}
.fb{{background:var(--surface);border:1px solid var(--line);color:var(--ink2);border-radius:999px;
 padding:6px 13px;font:inherit;font-size:13px;cursor:pointer}}
.fb:hover{{border-color:var(--ink3)}}
.fb.on{{background:var(--accent);border-color:var(--accent);color:var(--surface);font-weight:600}}
.fsep{{width:1px;background:var(--line);margin:2px 5px}}
.rules{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:6px 20px 16px}}
.rules li{{margin:9px 0;color:var(--ink2)}} .rules li b{{color:var(--ink)}}
.matrix td{{text-align:center;font-variant-numeric:tabular-nums}}
.matrix td.dash{{color:var(--ink3)}} .matrix td.hi{{font-weight:700}}
.matrix thead th:not(:first-child){{text-align:center}}
footer{{margin-top:38px;color:var(--ink3);font-size:12.5px;border-top:1px solid var(--line);padding-top:16px}}
footer a{{color:var(--ink2)}}
.empty{{display:none;padding:26px;text-align:center;color:var(--ink3);background:var(--surface);
 border:1px solid var(--line);border-radius:12px}}
@media(max-width:640px){{.c-niv .nivt,.c-seats,thead .th-seats{{display:none}}
 h1{{font-size:23px}} .wrap{{padding:20px 13px 56px}} .tab{{margin-right:12px;font-size:13.5px}}}}
</style></head><body>
<div class="wrap">
<header class="top">
  <div>
    <h1>Sorteo Bernabéu</h1>
    <p class="sub">Reparto de los dos abonos entre Pablo, Víctor, Jorge y Alberto.
    Todos los partidos que el Real Madrid juega en casa.</p>
  </div>
  <button id="tt" aria-label="Cambiar tema">◐ Tema</button>
</header>

<div class="tabs" role="tablist">
  <button class="tab" role="tab" aria-selected="true" data-s="2627">2026/27<span class="tg">Actual</span></button>
  <button class="tab" role="tab" aria-selected="false" data-s="2526">2025/26<span class="tg">Cerrada</span></button>
</div>

{season_html("2627", D27, True)}
{season_html("2526", D26, False)}

<footer>
  Calendario de LaLiga 26/27 según el sorteo oficial (30 jun 2026) publicado por
  <a href="https://www.realmadrid.com/es-ES/noticias/futbol/primer-equipo/actualidad/el-calendario-del-real-madrid-para-la-liga-2026-27-30-06-2026">Realmadrid.com</a>;
  fechas de Champions según <a href="https://www.uefa.com/uefachampionsleague/">UEFA</a> y de Copa
  del Rey según la <a href="https://rfef.es/es/noticias/la-temporada-202627-ya-tiene-establecidas-sus-fechas-clave">RFEF</a>.
  La temporada 2025/26 procede del Excel del sorteo del año pasado.
  Documento de consulta — si hay cambios o intercambios, se anotan aparte.
</footer>
</div>
<script>
(function(){{
  var r=document.documentElement;
  document.getElementById('tt').addEventListener('click',function(){{
    var d=r.getAttribute('data-theme')==='dark'||
      (!r.getAttribute('data-theme')&&matchMedia('(prefers-color-scheme:dark)').matches);
    r.setAttribute('data-theme',d?'light':'dark');}});

  // pestañas de temporada
  var tabs=[].slice.call(document.querySelectorAll('.tab'));
  function show(k){{
    tabs.forEach(function(t){{t.setAttribute('aria-selected',t.dataset.s===k);}});
    [].forEach.call(document.querySelectorAll('.season'),function(s){{s.hidden=s.id!=='s'+k;}});
    history.replaceState(null,'',k==='2627'?location.pathname:'#'+k);
  }}
  tabs.forEach(function(t){{t.addEventListener('click',function(){{show(t.dataset.s);}});}});
  function fromHash(){{ show(location.hash==='#2526'?'2526':'2627'); }}
  window.addEventListener('hashchange',fromHash);
  fromHash();

  // filtros, independientes por temporada
  [].forEach.call(document.querySelectorAll('.season'),function(sec){{
    var comp='ALL',who=null,
        all=[].slice.call(sec.querySelectorAll('.cal tbody tr')),
        empty=sec.querySelector('.empty');
    function apply(){{
      var vis=0,head=null,hv=false;
      all.forEach(function(tr){{
        if(tr.classList.contains('mrow')){{if(head)head.style.display=hv?'':'none';head=tr;hv=false;return;}}
        var ok=(comp==='ALL'||tr.dataset.comp===comp)&&
               (!who||tr.dataset.who.split('|').indexOf(who)>-1);
        tr.style.display=ok?'':'none'; if(ok){{vis++;hv=true;}}}});
      if(head)head.style.display=hv?'':'none';
      empty.style.display=vis?'none':'block';
    }}
    sec.querySelector('.flt').addEventListener('click',function(e){{
      var t=e.target.closest('.fb'); if(!t)return;
      if(t.dataset.comp){{comp=t.dataset.comp;
        [].forEach.call(this.querySelectorAll('.fb[data-comp]'),function(x){{x.classList.toggle('on',x===t);}});
      }}else{{var same=t.classList.contains('on'); who=same?null:t.dataset.who;
        [].forEach.call(this.querySelectorAll('.fb[data-who]'),function(x){{x.classList.toggle('on',!same&&x===t);}});}}
      apply();}});
  }});
}})();
</script>
</body></html>"""

open("index.html", "w", encoding="utf-8").write(HTML)
print("OK", len(HTML), "bytes")
for name, D in (("26/27", D27), ("25/26", D26)):
    t, l, e, pr, bc, sc = stats(D)
    print(name, len(D), "partidos ·", sum(t.values()), "entradas ·", dict(t))
