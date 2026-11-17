from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from core import compras, theme
from core.grid import grid
from core.http import APIError
from core.ui import aviso_api

theme.hero("🤝", "Atas de registro de preços e carona",
           "Atas vigentes que contêm o seu item: <b>preço atual</b> praticado, <b>saldo para adesão</b> (carona, art. 86 da "
           "Lei 14.133/2021) e atas <b>vencendo</b> — o órgão precisará licitar de novo em breve.")

c1, c2 = st.columns([1.2, 1])
codigo = c1.text_input("Código CATMAT", value=st.session_state.get("catmat_sel", ""),
                       help="Não sabe o código? Descubra na tela Preços históricos.")
janela = c2.select_slider("Atas assinadas nos últimos", ["6 meses", "12 meses", "18 meses", "24 meses"], value="12 meses")
if not codigo.strip():
    st.stop()
meses = int(janela.split()[0])
try:
    with st.spinner("Consultando atas…"):
        df = compras.atas_por_item(codigo.strip(), date.today() - timedelta(days=30 * meses), date.today())
except APIError as e:
    aviso_api(e); st.stop()
if df.empty:
    st.info("Nenhuma ata encontrada para esse item no período.")
    st.stop()

vig = df[df.dias_para_vencer >= 0]
vencendo = vig[vig.dias_para_vencer <= 90]
st.markdown(f"**{df.descricaoItem.iloc[0][:200]}**")
theme.kpis([
    {"rotulo": "Atas vigentes", "valor": len(vig), "formato": "int", "icone": "📜", "cor": theme.INDIGO},
    {"rotulo": "Vencem em 90 dias", "valor": len(vencendo), "formato": "int", "icone": "🔔", "cor": theme.ROSA,
     "sub": "nova licitação à vista"},
    {"rotulo": "Preço mediano (vigentes)", "valor": vig.valorUnitario.median() if len(vig) else None, "formato": "brl",
     "icone": "💲", "cor": theme.VERDE},
    {"rotulo": "Fornecedores", "valor": df.niFornecedor.nunique(), "formato": "int", "icone": "🏭", "cor": theme.AMBAR},
])

cols = {
    "dias_para_vencer": {"tipo": "dias", "titulo": "Vence em", "fixa": True, "largura": 140},
    "nomeUnidadeGerenciadora": {"titulo": "Órgão gerenciador", "largura": 240},
    "nomeRazaoSocialFornecedor": {"titulo": "Fornecedor (detentor)", "largura": 230},
    "valorUnitario": {"tipo": "brl", "titulo": "Preço unit.", "largura": 130},
    "quantidadeHomologadaItem": {"tipo": "num", "titulo": "Qtd. registrada", "largura": 130},
    "maximoAdesao": {"tipo": "num", "titulo": "Limite p/ adesões", "largura": 140},
    "quantidadeEmpenhada": {"tipo": "num", "titulo": "Já empenhado", "largura": 120},
    "dataVigenciaFinal": {"tipo": "data", "titulo": "Vigência até", "largura": 120},
    "numeroAtaRegistroPreco": {"titulo": "Ata", "largura": 110},
    "link_pncp": {"tipo": "link", "titulo": "PNCP"},
}
aba1, aba2, aba3 = st.tabs(["🔔 Vencendo (oportunidade)", "📜 Todas as vigentes", "📈 Preço ao longo do tempo"])
with aba1:
    st.caption("Atas que terminam em até 90 dias: procure o órgão, apresente sua empresa e acompanhe o próximo edital "
               "(ele costuma reaparecer no PCA e no Radar).")
    grid(vencendo.sort_values("dias_para_vencer"), "atas_venc", cols, selecao=False)
with aba2:
    sel, _ = grid(vig.sort_values("valorUnitario"), "atas_vig", cols)
    if sel is not None:
        st.session_state.cnpj_sel = sel["niFornecedor"]
        if st.button(f"🏆 Raio-X do fornecedor {sel['nomeRazaoSocialFornecedor']}"):
            st.switch_page("views/concorrentes.py")
with aba3:
    st.plotly_chart(px.scatter(df, x="dataAssinatura", y="valorUnitario", size="quantidadeHomologadaItem",
                               color="nomeRazaoSocialFornecedor", hover_name="nomeUnidadeGerenciadora",
                               labels={"dataAssinatura": "", "valorUnitario": "R$ unit."},
                               title="Preço registrado por data de assinatura").update_layout(showlegend=False, height=420),
                    use_container_width=True)
