"""Identidade visual: CSS global, cabeçalho, cartões de KPI animados (JS) e tema do Plotly."""
from __future__ import annotations

import html
import json

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

INDIGO, VIOLETA, CIANO, VERDE, AMBAR, ROSA, CINZA = (
    "#4f46e5", "#7c3aed", "#0891b2", "#059669", "#d97706", "#e11d48", "#64748b")
PALETA = [INDIGO, CIANO, VERDE, AMBAR, ROSA, VIOLETA, "#0ea5e9", "#84cc16"]

_CSS = """
<style>
.block-container {padding-top: 3.2rem; max-width: 1440px;}
header[data-testid="stHeader"] {background: transparent;}
h1, h2, h3 {letter-spacing: -0.02em;}
[data-testid="stSidebarNav"] a span {font-weight: 500;}
[data-testid="stSidebar"] [aria-current="page"] {background: linear-gradient(90deg,#4f46e533,#7c3aed22) !important;
  border-left: 3px solid #818cf8;}
div[data-testid="stVerticalBlockBorderWrapper"] {background:#fff; box-shadow:0 1px 2px #0f172a0d, 0 4px 16px #0f172a08;}
[data-testid="stMetric"] {background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:14px 16px;
  box-shadow:0 1px 2px #0f172a0a;}
[data-testid="stMetricValue"] {font-weight:700; font-size:1.55rem;}
.stTabs [data-baseweb="tab-list"] {gap:6px; background:#eef2ff; padding:5px; border-radius:12px;}
.stTabs [data-baseweb="tab"] {border-radius:9px; padding:6px 14px; height:auto;}
.stTabs [aria-selected="true"] {background:#fff; box-shadow:0 1px 3px #0f172a1f;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display:none;}
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primaryFormSubmit"] {
  background:linear-gradient(135deg,#4f46e5,#7c3aed); border:0; box-shadow:0 4px 14px #4f46e540;}
.rl-hero {background:radial-gradient(1200px 300px at 0% 0%,#6366f1 0%,#4338ca 40%,#1e1b4b 100%);
  color:#fff; border-radius:18px; padding:22px 26px; margin-bottom:18px; position:relative; overflow:hidden;}
.rl-hero:after {content:""; position:absolute; right:-60px; top:-60px; width:240px; height:240px;
  background:radial-gradient(circle,#22d3ee55,transparent 70%);}
.rl-hero h1 {color:#fff; margin:0; font-size:1.75rem; font-weight:800; padding:0;}
.rl-hero p {color:#c7d2fe; margin:.35rem 0 0 0; font-size:.95rem; max-width:900px;}
.rl-hero .rl-ic {font-size:1.6rem; margin-right:.5rem;}
.rl-badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem; font-weight:600;}
.rl-card {background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:14px 16px; margin-bottom:10px;}
.rl-card .t {font-weight:600; color:#0f172a;} .rl-card .s {color:#64748b; font-size:.85rem;}
.rl-tl {border-left:2px solid #c7d2fe; margin-left:6px; padding-left:16px; position:relative; margin-bottom:12px;}
.rl-tl:before {content:""; width:10px; height:10px; border-radius:50%; background:#4f46e5; position:absolute; left:-6px; top:5px;}
</style>
"""


def aplicar():
    st.markdown(_CSS, unsafe_allow_html=True)
    tpl = go.layout.Template()
    tpl.layout = go.Layout(
        font=dict(family="Inter, sans-serif", color="#0f172a", size=13),
        colorway=PALETA, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        title=dict(font=dict(size=15, color="#0f172a"), x=0, xanchor="left"),
        xaxis=dict(gridcolor="#eef2f7", zeroline=False, linecolor="#e2e8f0"),
        yaxis=dict(gridcolor="#eef2f7", zeroline=False, linecolor="#e2e8f0"),
        margin=dict(l=10, r=10, t=50, b=10), hoverlabel=dict(font_family="Inter"),
        legend=dict(orientation="h", y=-0.15),
    )
    pio.templates["radarlic"] = tpl
    pio.templates.default = "plotly_white+radarlic"


def hero(icone: str, titulo: str, subtitulo: str = ""):
    st.markdown(f"<div class='rl-hero'><h1><span class='rl-ic'>{icone}</span>{html.escape(titulo)}</h1>"
                f"<p>{subtitulo}</p></div>", unsafe_allow_html=True)


def badge(texto: str, cor: str = INDIGO) -> str:
    return f"<span class='rl-badge' style='background:{cor}1a;color:{cor}'>{html.escape(str(texto))}</span>"


def kpis(itens: list[dict], altura: int = 118):
    """Cartões animados (contagem progressiva em JS).
    item: {rotulo, valor(float), formato: 'brl'|'int'|'pct'|'txt', icone, cor, sub}"""
    dados = json.dumps([{**i, "valor": (None if i.get("valor") is None else
                                        (i["valor"] if i.get("formato") == "txt" else float(i["valor"])))}
                        for i in itens], ensure_ascii=False, default=str)
    components.html(f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;font-family:Inter,sans-serif;margin:0}}
.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;padding:2px}}
.c{{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:14px 16px;position:relative;overflow:hidden;
   box-shadow:0 1px 2px #0f172a0d,0 6px 18px #0f172a08;transition:transform .2s, box-shadow .2s;min-height:96px}}
.c:hover{{transform:translateY(-2px);box-shadow:0 10px 24px #0f172a14}}
.c:before{{content:"";position:absolute;inset:0 0 auto 0;height:4px;background:var(--k)}}
.l{{font-size:12px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:.04em;display:flex;gap:6px;align-items:center}}
.i{{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;background:color-mix(in srgb,var(--k) 14%,#fff)}}
.v{{font-size:24px;font-weight:800;color:#0f172a;margin-top:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.s{{font-size:12px;color:#64748b;margin-top:2px}}
</style>
<div class="g" id="g"></div>
<script>
const D={dados};
const fmt=(v,f)=>v==null?'—':f==='brl'?new Intl.NumberFormat('pt-BR',Math.abs(v)>=1e5?{{style:'currency',currency:'BRL',notation:'compact',maximumFractionDigits:1}}:{{style:'currency',currency:'BRL',maximumFractionDigits:Math.abs(v)>=1e4?0:2}}).format(v)
 :f==='pct'?new Intl.NumberFormat('pt-BR',{{maximumFractionDigits:1}}).format(v)+'%':f==='txt'?v
 :new Intl.NumberFormat('pt-BR',{{maximumFractionDigits:0}}).format(v);
const g=document.getElementById('g');
D.forEach((d,ix)=>{{const c=document.createElement('div');c.className='c';c.style.setProperty('--k',d.cor||'#4f46e5');
 c.innerHTML=`<div class="l"><span class="i">${{d.icone||'•'}}</span>${{d.rotulo}}</div><div class="v" id="v${{ix}}">${{fmt(d.formato==='txt'?d.valor:0,d.formato)}}</div><div class="s">${{d.sub||''}}</div>`;
 g.appendChild(c);
 if(d.formato!=='txt'&&d.valor!=null){{const t0=performance.now(),T=900;const el=c.querySelector('.v');
  const step=n=>{{const p=Math.min(1,(n-t0)/T),e=1-Math.pow(1-p,3);el.textContent=fmt(d.valor*e,d.formato);if(p<1)requestAnimationFrame(step)}};
  requestAnimationFrame(step);}}
 else if(d.valor==null) c.querySelector('.v').textContent='—';
}});
// reduz a fonte até o valor caber no cartão (evita "R$ 1.390,…")
const ajustar=()=>document.querySelectorAll('.v').forEach(el=>{{let f=24;el.style.fontSize=f+'px';
  while(el.scrollWidth>el.clientWidth&&f>13){{f--;el.style.fontSize=f+'px';}}}});
setTimeout(ajustar,950); window.addEventListener('resize',ajustar);
</script>""", height=altura)
