from datetime import date

import plotly.express as px
import streamlit as st

from core import compras
from core.http import APIError
from core.ui import brl, aviso_api

st.title("🗓️ Compras futuras — Plano de Contratações Anual (PCA)")
st.caption("Cada órgão publica o que pretende comprar no ano seguinte (art. 12, VII, da Lei 14.133/2021). "
           "É o melhor sinal de **editais que ainda vão abrir**: dá tempo de prospectar, cadastrar o "
           "produto e negociar com fornecedores antes do edital sair.")

c1, c2, c3 = st.columns([1, 1, 1])
classe = c1.number_input("Classe de material (4 dígitos)", 1000, 9999,
                         int(st.session_state.get("classe_sel") or 7510),
                         help="Ex.: 7510 material de expediente · 9310 papéis · 6515 instrumentos médicos. "
                              "A tela de Preços mostra a classe de cada CATMAT.")
ano = c2.selectbox("Ano do PCA", [date.today().year + 1, date.today().year, date.today().year - 1])
servico = c3.toggle("Serviço (CATSER)")
filtro = st.text_input("Filtrar por texto (item, órgão ou UF)")

try:
    with st.spinner("Consultando PCA…"):
        df = compras.pca_por_classe(int(classe), int(ano), servico)
except APIError as e:
    aviso_api(e); st.stop()

if df.empty:
    st.info("Nenhuma demanda planejada para essa classe/ano. PCAs do ano seguinte vão sendo publicados ao longo do ano corrente.")
    st.stop()

if len(df) >= 3000:
    st.caption("ℹ️ Mostrando as primeiras 3.000 demandas da classe. Use o filtro de texto para focar.")
if filtro:
    f = filtro.lower()
    df = df[df.apply(lambda r: f in f"{r.get('descricaoItemCatalogo', '')} {r.get('nomeUasg', '')} "
                                   f"{r.get('descricaoObjetoDfd', '')}".lower(), axis=1)]

k = st.columns(3)
k[0].metric("Demandas planejadas", len(df))
k[1].metric("Valor planejado", brl(df.valorTotalItem.sum(), 0))
k[2].metric("Órgãos (UASG)", df.codigoUasg.nunique())

c1, c2 = st.columns(2)
top_org = df.groupby("nomeUasg").valorTotalItem.sum().nlargest(12).reset_index()
c1.plotly_chart(px.bar(top_org, x="valorTotalItem", y="nomeUasg", orientation="h",
                       title="Maiores compradores planejados", labels={"valorTotalItem": "R$"}).update_yaxes(autorange="reversed", title=""),
                use_container_width=True)
crono = df.dropna(subset=["dataPrevistaFormalizacaoDemanda"]) \
    .set_index("dataPrevistaFormalizacaoDemanda").valorTotalItem.resample("MS").sum().reset_index()
c2.plotly_chart(px.bar(crono, x="dataPrevistaFormalizacaoDemanda", y="valorTotalItem",
                       title="Quando pretendem comprar",
                       labels={"dataPrevistaFormalizacaoDemanda": "", "valorTotalItem": "R$"}), use_container_width=True)

cols = [c for c in ["dataPrevistaFormalizacaoDemanda", "nomeUasg", "codigoItemCatalogo", "descricaoItemCatalogo",
                    "quantidadeItem", "siglaUnidadeFornecimento", "valorUnitarioItem", "valorTotalItem",
                    "descricaoObjetoDfd", "nivelPrioridadeDfd"] if c in df]
st.dataframe(df[cols].sort_values("dataPrevistaFormalizacaoDemanda"), hide_index=True, use_container_width=True,
             column_config={"valorUnitarioItem": st.column_config.NumberColumn("vlr unit.", format="R$ %.2f"),
                            "valorTotalItem": st.column_config.NumberColumn("vlr total", format="R$ %.2f"),
                            "dataPrevistaFormalizacaoDemanda": st.column_config.DateColumn("previsão", format="MM/YYYY"),
                            "descricaoItemCatalogo": st.column_config.TextColumn("item", width="large")})
st.download_button("⬇️ Exportar (CSV)", df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                   f"pca_{classe}_{ano}.csv")
