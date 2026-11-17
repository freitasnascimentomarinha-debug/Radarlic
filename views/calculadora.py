import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import theme
from core.grid import grid

from core.pricing import Entrada, REGIMES, preco_venda, margem_no_preco, decompor, limite_inexequivel
from core.ui import brl, pct

theme.hero("🧮", "Calculadora de margem e chance de vencer",
           "Preço pelo <b>markup divisor</b> (percentuais sobre o preço de venda, não sobre o custo), lance mínimo, "
           "ponto de equilíbrio e — com o histórico de preços — a <b>probabilidade de vencer</b> e o <b>preço ótimo</b>.")

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
    theme.kpis([
        {"rotulo": "Preço proposto", "valor": p_alvo, "formato": "brl", "icone": "🎯", "cor": theme.INDIGO,
         "sub": f"margem {pct(margem)}"},
        {"rotulo": "Lance mínimo", "valor": p_min, "formato": "brl", "icone": "⬇", "cor": theme.AMBAR,
         "sub": f"margem {pct(margem_min)}"},
        {"rotulo": "Equilíbrio", "valor": p_zero, "formato": "brl", "icone": "⚖", "cor": theme.ROSA, "sub": "lucro zero"},
    ], altura=112)
    theme.kpis([
        {"rotulo": "Faturamento", "valor": p_alvo * qtd, "formato": "brl", "icone": "💰", "cor": theme.CIANO},
        {"rotulo": "Lucro líquido", "valor": (p_alvo - p_zero) * qtd if p_zero else None, "formato": "brl",
         "icone": "📈", "cor": theme.VERDE},
        {"rotulo": "Despesas s/ preço", "valor": e.despesas_pct, "formato": "pct", "icone": "🧾", "cor": theme.CINZA},
    ], altura=112)

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
    tl = pd.DataFrame(linhas).drop_duplicates("margem %").rename(
        columns={"margem %": "margem", "preço unit.": "preco", "desconto s/ ref. %": "desconto"})
    grid(tl, "lances", {"margem": {"tipo": "pct", "titulo": "Margem"}, "preco": {"tipo": "brl", "titulo": "Preço unit."},
                        "total": {"tipo": "brl", "titulo": "Total"}, "desconto": {"tipo": "pct", "titulo": "Desconto s/ ref."}},
         selecao=False, busca=False)
    st.caption("Dica: em pregão eletrônico os lances costumam ser em reais com até 2–4 casas decimais, "
               "conforme o edital. Leve esta tabela para a sessão de disputa.")


# ------------------------------------------------------------------ chance de vencer
st.markdown("### 🎲 Chance de vencer e preço ótimo")
hist = st.session_state.get("precos_hist")
if not hist or len(hist.get("precos", [])) < 5:
    st.info("Abra **Preços históricos**, pesquise o item (mesma unidade de fornecimento) e clique em "
            "**Calcular margem e chance de vencer** para trazer os preços vencedores para cá.")
else:
    P = np.sort(np.array(hist["precos"], dtype=float))
    st.caption(f"Base: {len(P)} preços homologados do item {hist['codigo']} (unidade {hist.get('unidade', '')}, sem discrepantes). Chance de vencer a um preço p = fração das "
               "compras passadas em que o preço vencedor foi maior ou igual a p (você teria ganho). É uma estimativa "
               "empírica: confira se a unidade de fornecimento é a mesma do seu custo.")
    ch_min = st.slider("Chance mínima aceitável para o preço ótimo (%)", 5, 90, 30, 5,
                       help="Evita que poucos preços altos fora da curva puxem o 'ótimo' para um valor improvável.") / 100
    chance = lambda p: float((P >= p).mean()) if p is not None else 0.0  # noqa: E731
    grade = np.linspace(max(0.01, min(P.min(), p_zero) * 0.9), max(P.max(), p_alvo) * 1.05, 400)
    ch = np.array([chance(x) for x in grade])
    lucro_esp = np.where(grade > p_zero, (grade - p_zero) * qtd * ch, 0)
    validos = np.where(ch >= ch_min, lucro_esp, 0)
    p_otimo = float(grade[validos.argmax()]) if validos.max() > 0 else None
    theme.kpis([
        {"rotulo": "Chance no preço proposto", "valor": 100 * chance(p_alvo), "formato": "pct", "icone": "🎯", "cor": theme.INDIGO},
        {"rotulo": "Chance no lance mínimo", "valor": 100 * chance(p_min), "formato": "pct", "icone": "⬇", "cor": theme.AMBAR},
        {"rotulo": "Preço ótimo", "valor": p_otimo, "formato": "brl", "icone": "⭐", "cor": theme.VERDE,
         "sub": f"chance {pct(100 * chance(p_otimo))} · margem {pct(margem_no_preco(e, p_otimo))}" if p_otimo else "custo acima do mercado"},
        {"rotulo": "Lucro esperado no ótimo", "valor": float(validos.max()) if p_otimo else None, "formato": "brl",
         "icone": "📈", "cor": theme.CIANO, "sub": "chance × lucro"},
    ])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grade, y=100 * ch, name="Chance de vencer (%)", line=dict(width=3, color=theme.INDIGO),
                             fill="tozeroy", fillcolor="rgba(79,70,229,.08)"))
    fig.add_trace(go.Scatter(x=grade, y=lucro_esp, name="Lucro esperado (R$)", yaxis="y2",
                             line=dict(width=2, dash="dot", color=theme.VERDE)))
    for x, nome, cor, simb in [(p_alvo, "Proposto", theme.INDIGO, "circle"), (p_min, "Lance mínimo", theme.AMBAR, "diamond"),
                               (p_zero, "Equilíbrio", theme.ROSA, "x"), (p_otimo, "Ótimo", theme.VERDE, "star")]:
        if x:
            fig.add_vline(x=x, line=dict(color=cor, dash="dash", width=1))
            fig.add_trace(go.Scatter(x=[x], y=[100 * chance(x)], mode="markers", name=f"{nome}: {brl(x)} ({100 * chance(x):.0f}%)",
                                     marker=dict(size=13, color=cor, symbol=simb, line=dict(color="#fff", width=1.5))))
    fig.update_layout(height=470, xaxis_title="Preço unitário (R$)", legend=dict(orientation="h", y=-0.22),
                      yaxis=dict(title="Chance (%)", range=[0, 105]),
                      yaxis2=dict(title="Lucro esperado (R$)", overlaying="y", side="right", showgrid=False))
    st.plotly_chart(fig, use_container_width=True)
    if p_otimo and p_otimo < p_min:
        st.warning("O preço ótimo fica abaixo do seu lance mínimo: o mercado está apertado para o seu custo. "
                   "Reveja fornecedor, frete ou regime tributário.")
