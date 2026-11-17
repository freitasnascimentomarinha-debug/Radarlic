from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from core import compras, cnpj as cnpjmod, storage
from core.http import APIError
from core.ui import brl, aviso_api

cart = storage.carregar()
st.title("🏆 Concorrentes")

aba_ramo, aba_emp = st.tabs(["Ranking do ramo", "Raio-X de uma empresa"])

with aba_ramo:
    st.caption("Quem mais vence nos itens do seu ramo. Informe um ou mais códigos CATMAT/CATSER "
               "(os do seu perfil vêm preenchidos).")
    c1, c2 = st.columns([3, 1])
    codigos_txt = c1.text_input("Códigos (separados por vírgula)",
                                value=", ".join(cart["perfil"].get("catmats") or
                                                ([st.session_state.catmat_sel] if st.session_state.get("catmat_sel") else [])))
    meses = c2.selectbox("Período", [6, 12, 24], index=1, format_func=lambda m: f"{m} meses")
    codigos = [c.strip() for c in codigos_txt.split(",") if c.strip()]
    if codigos and st.button("Gerar ranking", type="primary"):
        frames = []
        try:
            for c in codigos:
                with st.spinner(f"Lendo compras do item {c}…"):
                    d = compras.precos_praticados(c, False, None, date.today() - timedelta(days=30 * meses), date.today())
                    if d.empty:
                        d = compras.precos_praticados(c, True, None, date.today() - timedelta(days=30 * meses), date.today())
                    frames.append(d.assign(codigo=c))
        except APIError as e:
            aviso_api(e)
        base = pd.concat(frames) if frames else pd.DataFrame()
        st.session_state.ranking_base = base
    base = st.session_state.get("ranking_base", pd.DataFrame())
    if not base.empty and "niFornecedor" in base:
        base = base.assign(valor=base.precoUnitario * base.quantidade)
        rk = base.groupby(["niFornecedor", "nomeFornecedor"]).agg(
            vitorias=("precoUnitario", "count"), valor_total=("valor", "sum"),
            itens_distintos=("codigo", "nunique"), orgaos=("nomeUasg", "nunique"),
            ufs=("estado", lambda s: ", ".join(sorted(set(s.dropna())))),
            ultima=("dataCompra", "max")).reset_index().sort_values("valor_total", ascending=False)
        k = st.columns(3)
        k[0].metric("Fornecedores distintos", len(rk))
        k[1].metric("Compras analisadas", len(base))
        top5 = rk.head(5).valor_total.sum() / rk.valor_total.sum() if rk.valor_total.sum() else 0
        k[2].metric("Concentração (top 5)", f"{100 * top5:.0f}%",
                    help="Fatia do valor ganho pelos 5 maiores. Alta concentração = mercado dominado.")
        st.plotly_chart(px.bar(rk.head(15), x="valor_total", y="nomeFornecedor", orientation="h",
                               title="Top 15 por valor vendido",
                               labels={"valor_total": "R$", "nomeFornecedor": ""}).update_yaxes(autorange="reversed"),
                        use_container_width=True)
        st.caption("Clique numa empresa para ver tudo o que ela forneceu.")
        ev = st.dataframe(rk, hide_index=True, use_container_width=True, on_select="rerun",
                          selection_mode="single-row", key="rk",
                          column_config={"valor_total": st.column_config.NumberColumn("valor total", format="R$ %.2f"),
                                         "ultima": st.column_config.DateColumn("última venda", format="DD/MM/YYYY")})
        if ev.selection.rows:
            st.session_state.cnpj_sel = rk.iloc[ev.selection.rows[0]]["niFornecedor"]
            st.info("Empresa selecionada — abra a aba **Raio-X de uma empresa**.")

with aba_emp:
    c1, c2 = st.columns([2, 1])
    cnpj = c1.text_input("CNPJ do concorrente", value=st.session_state.get("cnpj_sel", ""))
    meses_e = c2.selectbox("Histórico", [6, 12, 24], index=1, format_func=lambda m: f"{m} meses", key="me")
    if cnpj:
        cad = cnpjmod.consultar(cnpj)
        if cad:
            st.subheader(cad.get("razao_social", ""))
            k = st.columns(4)
            k[0].metric("Porte", cad.get("porte") or "—")
            k[1].metric("Abertura", cad.get("data_inicio_atividade") or "—")
            k[2].metric("Capital social", brl(cad.get("capital_social")))
            k[3].metric("Sede", f"{cad.get('municipio', '')}/{cad.get('uf', '')}")
            st.caption(f"CNAE principal: {cad.get('cnae_fiscal')} – {cad.get('cnae_fiscal_descricao')} · "
                       f"Situação: {cad.get('descricao_situacao_cadastral')} · "
                       f"Simples: {'sim' if cad.get('opcao_pelo_simples') else 'não'}")
            socios = cad.get("qsa") or []
            if socios:
                with st.expander(f"Quadro societário ({len(socios)})"):
                    st.dataframe(pd.DataFrame(socios)[["nome_socio", "qualificacao_socio", "data_entrada_sociedade"]],
                                 hide_index=True, use_container_width=True)
        else:
            st.caption(f"CNPJ {cnpjmod.formatar(cnpj)} — dados cadastrais indisponíveis no momento.")

        try:
            # A API limita a janela de datas; busca em blocos de 12 meses
            hoje, frames = date.today(), []
            with st.spinner("Buscando itens homologados para a empresa (PNCP)…"):
                fim = hoje
                restante = meses_e
                while restante > 0:
                    m = min(12, restante)
                    ini = fim - timedelta(days=30 * m)
                    frames.append(compras.itens_vencidos_fornecedor(cnpj, ini, fim))
                    fim, restante = ini, restante - m
            its = pd.concat([f for f in frames if not f.empty]) if any(not f.empty for f in frames) else pd.DataFrame()
        except APIError as e:
            aviso_api(e); its = pd.DataFrame()

        if its.empty:
            st.info("Nenhum item homologado (Lei 14.133) encontrado nesse período.")
        else:
            k = st.columns(3)
            k[0].metric("Itens ganhos", len(its))
            k[1].metric("Valor homologado", brl(its.valorTotalHomologado.sum(), 0))
            k[2].metric("Órgãos atendidos", its.orgaoEntidadeCnpj.nunique())
            mens = its.set_index("dataResultadoPncp").valorTotalHomologado.resample("MS").sum().reset_index()
            st.plotly_chart(px.bar(mens, x="dataResultadoPncp", y="valorTotalHomologado",
                                   title="Valor ganho por mês",
                                   labels={"dataResultadoPncp": "", "valorTotalHomologado": "R$"}), use_container_width=True)
            # o endpoint de resultados não traz a descrição: busca nos itens de cada contratação
            ids = its.sort_values("dataResultadoPncp", ascending=False).idContratacaoPNCP.drop_duplicates()
            limite = st.slider("Descrever itens das N contratações mais recentes", 0, min(80, len(ids)),
                               min(25, len(ids)), help="Cada contratação é uma consulta ao PNCP.")
            desc = {}
            barra = st.progress(0.0, "Carregando descrições…") if limite else None
            from core import pncp
            for i, pid in enumerate(ids.head(limite)):
                try:
                    d = pncp.itens(pid)
                    for _, r in d.iterrows():
                        desc[(pid, int(r["numeroItem"]))] = (r.get("descricao"), r.get("catalogoCodigoItem"),
                                                             r.get("unidadeMedida"))
                except APIError:
                    pass
                barra.progress((i + 1) / limite)
            if barra:
                barra.empty()
            chave = list(zip(its.idContratacaoPNCP, its.numeroItemPncp.astype(int)))
            its["descricao"] = [desc.get(c, (None,))[0] for c in chave]
            its["catmat"] = [desc.get(c, (None, None))[1] for c in chave]
            its["unidade"] = [desc.get(c, (None, None, None))[2] for c in chave]
            cols = [c for c in ["dataResultadoPncp", "descricao", "catmat", "unidade", "idContratacaoPNCP", "numeroItemPncp", "unidadeOrgaoUfSigla",
                                "quantidadeHomologada", "valorUnitarioHomologado", "valorTotalHomologado",
                                "percentualDesconto", "aplicacaoBeneficioMeepp"] if c in its]
            st.markdown("**Todos os itens fornecidos**")
            tab = its[cols].sort_values("dataResultadoPncp", ascending=False)
            ev = st.dataframe(tab, hide_index=True, use_container_width=True, on_select="rerun",
                              selection_mode="single-row", key="its_emp",
                              column_config={"valorUnitarioHomologado": st.column_config.NumberColumn("vlr unit.", format="R$ %.2f"),
                                             "valorTotalHomologado": st.column_config.NumberColumn("vlr total", format="R$ %.2f"),
                                             "descricao": st.column_config.TextColumn("descrição", width="large"),
                                             "idContratacaoPNCP": "contratação PNCP"})
            if its["descricao"].notna().any():
                top = its.dropna(subset=["descricao"]).assign(d=lambda x: x.descricao.str[:70]) \
                    .groupby("d").valorTotalHomologado.sum().nlargest(10).reset_index()
                st.plotly_chart(px.bar(top, x="valorTotalHomologado", y="d", orientation="h",
                                       title="Itens que mais faturaram").update_yaxes(autorange="reversed", title=""),
                                use_container_width=True)
            if ev.selection.rows:
                r = tab.iloc[ev.selection.rows[0]]
                st.session_state.edital_sel = r["idContratacaoPNCP"]
                if st.button("📄 Abrir esta contratação (itens, descrição e edital)"):
                    st.switch_page("views/edital.py")
            st.download_button("⬇️ Exportar (CSV)", its.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                               f"itens_{cnpj}.csv", "text/csv")
