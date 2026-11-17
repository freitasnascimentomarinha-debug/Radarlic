from datetime import date, timedelta

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from core import compras, pncp, theme
from core.grid import grid
from core.http import APIError
from core.ui import brl, pct, aviso_api

theme.hero("💰", "Preços históricos",
           "Preços <b>homologados</b> em compras públicas por código CATMAT (material) ou CATSER (serviço): "
           "média, mediana, mínimo e máximo médios, por UF, marca e fornecedor.")

with st.expander("🔍 Não sei o código CATMAT — descobrir pelo nome do produto",
                 expanded=not st.session_state.get("catmat_sel")):
    txt = st.text_input("Descreva o produto", placeholder="ex.: papel A4 75g")
    if st.button("Descobrir códigos") and txt:
        try:
            with st.spinner("Procurando o produto em editais recentes do PNCP…"):
                st.session_state.descobertos = compras.descobrir_catmat(txt)
        except APIError as e:
            aviso_api(e)
    desc = st.session_state.get("descobertos")
    if desc is not None:
        if desc.empty:
            st.warning("Nenhum código encontrado. Tente termos mais genéricos (ex.: 'papel sulfite').")
        else:
            st.caption("Clique no código certo:")
            esc, _ = grid(desc, "desc_tab", {"codigo": {"titulo": "Código", "largura": 110, "fixa": True},
                                             "ocorrencias": {"tipo": "num", "titulo": "Ocorrências", "largura": 120},
                                             "descricao": {"tipo": "longo", "titulo": "Descrição"},
                                             "unidade": {"titulo": "Unidade", "largura": 120}}, busca=False)
            if esc is not None and esc["codigo"] != st.session_state.get("catmat_sel"):
                st.session_state.catmat_sel = esc["codigo"]
                st.rerun()

c1, c2, c3, c4 = st.columns([1.2, 1, 1.4, 1])
codigo = c1.text_input("Código CATMAT/CATSER", value=st.session_state.get("catmat_sel", ""))
servico = c2.toggle("É serviço (CATSER)", value=st.session_state.get("catmat_servico", False))
periodo = c3.select_slider("Período", ["6 meses", "12 meses", "24 meses", "36 meses"], value="24 meses")
uf = c4.selectbox("UF", ["Todas"] + pncp.UFS)
outl = st.toggle("Descartar preços discrepantes (inexequíveis/excessivos – critério IQR)", value=True)

if not codigo.strip():
    st.stop()
st.session_state.catmat_sel = codigo.strip()

meses = int(periodo.split()[0])
try:
    with st.spinner("Buscando preços praticados…"):
        info = {} if servico else compras.item_catmat(int(codigo)) if codigo.isdigit() else {}
        df = compras.precos_praticados(codigo.strip(), servico, None if uf == "Todas" else uf,
                                       date.today() - timedelta(days=30 * meses), date.today())
except APIError as e:
    aviso_api(e); st.stop()

if info:
    st.markdown(f"**{info.get('descricaoItem', '').strip()}**")
    st.caption(f"PDM {info.get('codigoPdm')} – {info.get('nomePdm')} · Classe {info.get('codigoClasse')} – {info.get('nomeClasse')}")
    st.session_state.classe_sel = info.get("codigoClasse")

if df.empty:
    st.warning("Sem compras registradas para esse código e filtros.")
    st.stop()

# Unidades de fornecimento diferentes distorcem a média (ex.: resma × caixa com 10 resmas)
unidades = df.unidade_fornecimento.value_counts()
if len(unidades) > 1:
    un = st.selectbox("Unidade de fornecimento (compare só a mesma unidade)", unidades.index,
                      format_func=lambda u: f"{u} ({unidades[u]} compras)")
    df = df[df.unidade_fornecimento == un]

stats, mensal = compras.estatisticas(df, outl)

_p = df["precoUnitario"].dropna()
if outl and len(_p) >= 5:  # mesma regra de descarte das estatísticas
    _q1, _q3 = _p.quantile([.25, .75]); _p = _p[(_p >= _q1 - 1.5 * (_q3 - _q1)) & (_p <= _q3 + 1.5 * (_q3 - _q1))]
st.session_state.precos_hist = {"codigo": codigo.strip(), "precos": _p.tolist(),
                                "unidade": df["unidade_fornecimento"].iloc[0] if len(df) else ""}
theme.kpis([
    {"rotulo": "Preço médio", "valor": stats["media"], "formato": "brl", "icone": "📊", "cor": theme.INDIGO},
    {"rotulo": "Mediana", "valor": stats["mediana"], "formato": "brl", "icone": "🎯", "cor": theme.VIOLETA,
     "sub": f"P25 {brl(stats['p25'])} · P75 {brl(stats['p75'])}"},
    {"rotulo": "Mínimo médio", "valor": stats["media_minimos"], "formato": "brl", "icone": "⬇", "cor": theme.VERDE,
     "sub": "média dos menores preços/mês"},
    {"rotulo": "Máximo médio", "valor": stats["media_maximos"], "formato": "brl", "icone": "⬆", "cor": theme.ROSA,
     "sub": "média dos maiores preços/mês"},
])
theme.kpis([
    {"rotulo": "Menor preço", "valor": stats["minimo"], "formato": "brl", "icone": "🥇", "cor": theme.CIANO},
    {"rotulo": "Maior preço", "valor": stats["maximo"], "formato": "brl", "icone": "🔺", "cor": theme.AMBAR},
    {"rotulo": "Compras analisadas", "valor": stats["n"], "formato": "int", "icone": "🧾", "cor": theme.INDIGO,
     "sub": f"{stats['descartados']} discrepantes descartadas"},
    {"rotulo": "Dispersão (CV)", "valor": 100 * stats["cv"] if stats["cv"] else None, "formato": "pct", "icone": "〰",
     "cor": theme.CINZA, "sub": "> 25% = mercado heterogêneo"},
])

fig = go.Figure()
fig.add_trace(go.Scatter(x=df.dataCompra, y=df.precoUnitario, mode="markers", name="Compras",
                         marker=dict(size=6, opacity=0.35), text=df.nomeFornecedor if "nomeFornecedor" in df else None))
for col, nome in [("min", "Mínimo do mês"), ("mean", "Média do mês"), ("max", "Máximo do mês")]:
    fig.add_trace(go.Scatter(x=mensal.index, y=mensal[col], mode="lines+markers", name=nome))
fig.update_layout(title="Evolução do preço unitário", yaxis_title="R$", height=420, legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns(2)
por_uf = df.groupby("estado").precoUnitario.agg(["count", "median", "min", "max"]).reset_index() \
    .rename(columns={"estado": "UF", "count": "compras", "median": "mediana", "min": "mínimo", "max": "máximo"})
with c1:
    st.markdown("**Por UF**")
    grid(por_uf.sort_values("compras", ascending=False), "por_uf",
         {"UF": {"largura": 70}, "compras": {"tipo": "num"}, "mediana": "brl", "mínimo": "brl", "máximo": "brl"},
         selecao=False, busca=False, pagina=10)
if "nomeFornecedor" in df:
    venc = df.groupby(["niFornecedor", "nomeFornecedor"]).agg(
        vitorias=("precoUnitario", "count"), preco_medio=("precoUnitario", "mean"),
        ufs=("estado", lambda s: ", ".join(sorted(set(s.dropna()))))).reset_index() \
        .sort_values("vitorias", ascending=False)
    with c2:
        st.markdown("**Quem mais vende este item** — clique para o raio-X")
        vsel, _ = grid(venc.head(50), "venc_tab", {
            "nomeFornecedor": {"titulo": "Fornecedor", "tipo": "longo", "min": 200},
            "vitorias": {"tipo": "num", "titulo": "Vitórias", "largura": 100},
            "preco_medio": {"tipo": "brl", "titulo": "Preço médio", "largura": 130},
            "ufs": {"titulo": "UFs", "largura": 120}}, busca=False, pagina=10)
        if vsel is not None:
            st.session_state.cnpj_sel = vsel["niFornecedor"]
            st.switch_page("views/concorrentes.py")

b1, b2 = st.columns(2)
if b1.button("🧮 Calcular margem e chance de vencer com estes preços", use_container_width=True):
    st.session_state.preco_ref = float(stats["mediana"])
    st.switch_page("views/calculadora.py")
b2.download_button("⬇️ Exportar compras (CSV) — serve de memória da pesquisa de preços",
                   df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                   f"precos_{codigo}.csv", "text/csv", use_container_width=True)

st.markdown("#### 🧾 Compras individuais")
grid(df.sort_values("dataCompra", ascending=False), "compras_ind", {
    "dataCompra": {"tipo": "data", "titulo": "Data", "largura": 110, "fixa": True},
    "precoUnitario": {"tipo": "brl", "titulo": "Preço unit.", "largura": 130},
    "quantidade": {"tipo": "num", "titulo": "Qtd.", "largura": 100},
    "unidade_fornecimento": {"titulo": "Unidade", "largura": 120},
    "marca": {"titulo": "Marca", "largura": 140},
    "nomeFornecedor": {"titulo": "Fornecedor", "largura": 220},
    "nomeUasg": {"titulo": "Órgão comprador", "largura": 240},
    "estado": {"titulo": "UF", "largura": 70},
    "descricaoItem": {"tipo": "longo", "titulo": "Descrição", "min": 260}}, selecao=False)

if "marca" in df and df.marca.notna().any():
    top = df.marca.str.upper().str.strip().value_counts().head(12).index
    dm = df.assign(marca=df.marca.str.upper().str.strip())
    st.plotly_chart(px.box(dm[dm.marca.isin(top)], x="marca", y="precoUnitario",
                           title="Preço por marca (12 mais vendidas)", labels={"precoUnitario": "R$", "marca": ""}), use_container_width=True)
