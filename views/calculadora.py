import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.pricing import Entrada, REGIMES, preco_venda, margem_no_preco, decompor, limite_inexequivel
from core.ui import brl, pct

st.title("🧮 Calculadora de margem e preço de lance")
st.caption("Forma o preço pelo *markup divisor*: todos os percentuais incidem sobre o **preço de venda**, "
           "não sobre o custo — o erro mais comum de quem começa em licitação.")

col_e, col_r = st.columns([1, 1.3])
with col_e:
    st.markdown("##### Custos por unidade")
    custo = st.number_input("Custo do produto (R$)", 0.0, value=10.0, step=0.5, format="%.2f")
    frete = st.number_input("Frete até o órgão (R$/un.)", 0.0, value=0.5, step=0.1, format="%.2f")
    outros = st.number_input("Outros custos diretos (embalagem, etiquetas…)", 0.0, value=0.0, format="%.2f")
    qtd = st.number_input("Quantidade", 1.0, value=float(st.session_state.get("qtd_ref", 100.0)), step=1.0)

    st.markdown("##### Tributos e despesas (% sobre o preço)")
    regime = st.selectbox("Regime tributário", list(REGIMES))
    st.caption(REGIMES[regime]["nota"])
    imp = st.number_input("Tributos (%)", 0.0, 60.0, float(REGIMES[regime]["impostos"]), 0.1)
    icms = st.number_input("ICMS / DIFAL (%)", 0.0, 30.0, 0.0, 0.5,
                           help="No Simples, já está na alíquota efetiva (deixe 0), salvo DIFAL interestadual.")
    comissao = st.number_input("Comissão de representante (%)", 0.0, 30.0, 0.0, 0.5)
    plataforma = st.number_input("Taxa da plataforma de disputa (%)", 0.0, 10.0, 0.0, 0.1)
    c1, c2 = st.columns(2)
    prazo = c1.number_input("Prazo de pagamento (dias)", 0, 180, 30)
    juros = c2.number_input("Custo do capital (% a.m.)", 0.0, 10.0, 1.5, 0.1)
    garantia = st.number_input("Custo da garantia contratual (%)", 0.0, 5.0, 0.0, 0.1,
                               help="Custo do seguro-garantia/caução como % do preço. A garantia em si é de até 5% (art. 98 da Lei 14.133).")
    margem = st.slider("Margem líquida desejada (%)", 0.0, 50.0, 15.0, 0.5)
    margem_min = st.slider("Margem mínima aceitável no lance (%)", 0.0, 30.0, 5.0, 0.5)

e = Entrada(custo, frete, outros, imp, icms, comissao, plataforma, prazo, juros, garantia, margem, qtd)

with col_r:
    p_alvo, p_min = preco_venda(e), preco_venda(e, margem_min)
    p_zero = preco_venda(e, 0)
    if p_alvo is None:
        st.error("Despesas + margem ≥ 100% do preço. Reduza percentuais.")
        st.stop()
    k = st.columns(3)
    k[0].metric("Preço proposto", brl(p_alvo), help=f"Margem de {pct(margem)}")
    k[1].metric("Lance mínimo", brl(p_min), help=f"Abaixo disso, margem < {pct(margem_min)}")
    k[2].metric("Ponto de equilíbrio", brl(p_zero), help="Preço com lucro zero")
    k = st.columns(3)
    k[0].metric("Faturamento", brl(p_alvo * qtd, 0))
    k[1].metric("Lucro líquido", brl((p_alvo - p_zero) * qtd if p_zero else None, 0))
    k[2].metric("Despesas sobre o preço", pct(e.despesas_pct))

    ref = st.number_input("Preço de referência do edital / histórico (R$/un.)", 0.0,
                          value=float(st.session_state.get("preco_ref", 0.0)), format="%.2f",
                          help="Venha da tela Preços históricos ou do item do edital.")
    if ref > 0:
        m_ref = margem_no_preco(e, ref)
        cor = "normal" if m_ref >= margem_min else "inverse"
        st.metric("Sua margem vendendo no preço de referência", pct(m_ref),
                  delta=f"{m_ref - margem:+.1f} p.p. vs. desejada".replace(".", ","), delta_color=cor)
        st.caption(f"Desconto máximo possível sobre a referência mantendo a margem mínima: "
                   f"**{pct(100 * (1 - p_min / ref))}** · Referência de inexequibilidade (75%): {brl(limite_inexequivel(ref))}")
        if p_min < limite_inexequivel(ref):
            st.warning("Seu lance mínimo fica abaixo de 75% da referência: o pregoeiro pode exigir prova de exequibilidade (planilha, notas de compra).")

    d = decompor(e, p_alvo)
    fig = go.Figure(go.Waterfall(
        x=list(d) + ["Preço"], y=list(d.values()) + [0],
        measure=["relative"] * len(d) + ["total"], text=[brl(v) for v in d.values()] + [brl(p_alvo)]))
    fig.update_layout(title="Composição do preço unitário", height=380, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Tabela de lances")
    linhas = []
    for m in [margem, *range(int(margem) - 2, -1, -2)]:
        p = preco_venda(e, m)
        if p:
            linhas.append({"margem %": m, "preço unit.": p, "total": p * qtd,
                           "desconto s/ ref. %": (100 * (1 - p / ref)) if ref else None})
    st.dataframe(pd.DataFrame(linhas).drop_duplicates("margem %"), hide_index=True, use_container_width=True,
                 column_config={"preço unit.": st.column_config.NumberColumn(format="R$ %.4f"),
                                "total": st.column_config.NumberColumn(format="R$ %.2f"),
                                "desconto s/ ref. %": st.column_config.NumberColumn(format="%.1f%%")})
    st.caption("Dica: em pregão eletrônico os lances costumam ser em reais com até 2–4 casas decimais, "
               "conforme o edital. Leve esta tabela para a sessão de disputa.")
