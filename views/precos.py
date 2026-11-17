from datetime import date, timedelta

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from core import compras, pncp
from core.http import APIError
from core.ui import brl, pct, aviso_api

st.title("💰 Preços históricos")
st.caption("Preços **homologados** em compras públicas (Compras.gov.br / PNCP), por código CATMAT (material) ou CATSER (serviço).")

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
            ev = st.dataframe(desc, hide_index=True, use_container_width=True, on_select="rerun",
                              selection_mode="single-row", key="desc_tab")
            if ev.selection.rows:
                st.session_state.catmat_sel = desc.iloc[ev.selection.rows[0]]["codigo"]
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

k = st.columns(4)
k[0].metric("Preço médio", brl(stats["media"]))
k[1].metric("Mediana", brl(stats["mediana"]))
k[2].metric("Mínimo médio (mensal)", brl(stats["media_minimos"]),
            help="Média dos menores preços de cada mês — referência de preço agressivo/vencedor.")
k[3].metric("Máximo médio (mensal)", brl(stats["media_maximos"]),
            help="Média dos maiores preços de cada mês.")
k = st.columns(4)
k[0].metric("Menor preço", brl(stats["minimo"]))
k[1].metric("Maior preço", brl(stats["maximo"]))
k[2].metric("Compras analisadas", stats["n"], help=f"{stats['descartados']} descartadas como discrepantes")
k[3].metric("Dispersão (CV)", pct(100 * stats["cv"]) if stats["cv"] else "—",
            help="Coeficiente de variação. Acima de 25% indica mercado heterogêneo (IN 65/2021 recomenda análise crítica).")

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
c1.markdown("**Por UF**")
c1.dataframe(por_uf.sort_values("compras", ascending=False), hide_index=True, use_container_width=True,
             column_config={c: st.column_config.NumberColumn(format="R$ %.2f") for c in ["mediana", "mínimo", "máximo"]})
if "nomeFornecedor" in df:
    venc = df.groupby(["niFornecedor", "nomeFornecedor"]).agg(
        vitorias=("precoUnitario", "count"), preco_medio=("precoUnitario", "mean"),
        ufs=("estado", lambda s: ", ".join(sorted(set(s.dropna()))))).reset_index() \
        .sort_values("vitorias", ascending=False)
    c2.markdown("**Quem mais vende este item**")
    ev = c2.dataframe(venc.head(30), hide_index=True, use_container_width=True, on_select="rerun",
                      selection_mode="single-row", key="venc_tab",
                      column_config={"preco_medio": st.column_config.NumberColumn("preço médio", format="R$ %.2f")})
    if ev.selection.rows:
        st.session_state.cnpj_sel = venc.iloc[ev.selection.rows[0]]["niFornecedor"]
        st.switch_page("views/concorrentes.py")

b1, b2 = st.columns(2)
if b1.button("🧮 Usar a mediana na calculadora de margem", use_container_width=True):
    st.session_state.preco_ref = float(stats["mediana"])
    st.switch_page("views/calculadora.py")
b2.download_button("⬇️ Exportar compras (CSV) — serve de memória da pesquisa de preços",
                   df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                   f"precos_{codigo}.csv", "text/csv", use_container_width=True)

with st.expander("Ver compras individuais"):
    cols = [c for c in ["dataCompra", "precoUnitario", "quantidade", "unidade_fornecimento", "marca",
                        "nomeFornecedor", "nomeUasg", "estado", "modalidade", "descricaoItem"] if c in df]
    st.dataframe(df[cols].sort_values("dataCompra", ascending=False), hide_index=True, use_container_width=True,
                 column_config={"precoUnitario": st.column_config.NumberColumn("preço", format="R$ %.2f")})

if "marca" in df and df.marca.notna().any():
    top = df.marca.str.upper().str.strip().value_counts().head(12).index
    dm = df.assign(marca=df.marca.str.upper().str.strip())
    st.plotly_chart(px.box(dm[dm.marca.isin(top)], x="marca", y="precoUnitario",
                           title="Preço por marca (12 mais vendidas)", labels={"precoUnitario": "R$", "marca": ""}), use_container_width=True)
