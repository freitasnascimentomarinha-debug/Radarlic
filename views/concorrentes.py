from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from core import compras, cnpj as cnpjmod, storage, theme
from core.grid import grid
from core.http import APIError
from core.ui import brl, aviso_api

cart = storage.carregar()
theme.hero("🏆", "Concorrentes",
           "Quem mais vence no seu ramo, a que preço e para quais órgãos — e o raio-X completo de qualquer CNPJ: "
           "cadastro na Receita e todos os itens que já forneceu ao governo.")

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
        top5 = rk.head(5).valor_total.sum() / rk.valor_total.sum() if rk.valor_total.sum() else 0
        theme.kpis([
            {"rotulo": "Fornecedores", "valor": len(rk), "formato": "int", "icone": "🏭", "cor": theme.INDIGO},
            {"rotulo": "Compras analisadas", "valor": len(base), "formato": "int", "icone": "🧾", "cor": theme.CIANO},
            {"rotulo": "Valor movimentado", "valor": rk.valor_total.sum(), "formato": "brl", "icone": "💰", "cor": theme.VERDE},
            {"rotulo": "Concentração top 5", "valor": 100 * top5, "formato": "pct", "icone": "🎯", "cor": theme.ROSA,
             "sub": "alta = mercado dominado"},
        ])
        st.plotly_chart(px.bar(rk.head(15), x="valor_total", y="nomeFornecedor", orientation="h",
                               title="Top 15 por valor vendido",
                               labels={"valor_total": "R$", "nomeFornecedor": ""}).update_yaxes(autorange="reversed"),
                        use_container_width=True)
        st.caption("Clique numa empresa para ver tudo o que ela forneceu.")
        rk.insert(0, "posicao", range(1, len(rk) + 1))
        esc, _ = grid(rk, "rk", {
            "posicao": {"titulo": "#", "largura": 65, "fixa": True},
            "nomeFornecedor": {"tipo": "longo", "titulo": "Fornecedor", "min": 340},
            "valor_total": {"tipo": "brl", "titulo": "Valor vendido", "largura": 150},
            "vitorias": {"tipo": "num", "titulo": "Vitórias", "largura": 100},
            "itens_distintos": {"tipo": "num", "titulo": "Itens", "largura": 85},
            "orgaos": {"tipo": "num", "titulo": "Órgãos", "largura": 95},
            "ufs": {"titulo": "UFs", "largura": 140},
            "ultima": {"tipo": "data", "titulo": "Última venda", "largura": 125}})
        if esc is not None:
            st.session_state.cnpj_sel = esc["niFornecedor"]
            st.success(f"**{esc['nomeFornecedor']}** selecionada — abra a aba **Raio-X de uma empresa**.")

with aba_emp:
    c1, c2 = st.columns([2, 1])
    cnpj = c1.text_input("CNPJ do concorrente", value=st.session_state.get("cnpj_sel", ""))
    meses_e = c2.selectbox("Histórico", [6, 12, 24], index=1, format_func=lambda m: f"{m} meses", key="me")
    if cnpj:
        cad = cnpjmod.consultar(cnpj)
        if cad:
            st.subheader(cad.get("razao_social", ""))
            ab = pd.to_datetime(cad.get("data_inicio_atividade"), errors="coerce")
            theme.kpis([
                {"rotulo": "Porte", "valor": cad.get("porte") or "—", "formato": "txt", "icone": "🏢", "cor": theme.INDIGO},
                {"rotulo": "Abertura", "valor": ab.strftime("%d/%m/%Y") if pd.notna(ab) else "—", "formato": "txt",
                 "icone": "📆", "cor": theme.CIANO, "sub": f"{(pd.Timestamp.today() - ab).days // 365} anos" if pd.notna(ab) else ""},
                {"rotulo": "Capital social", "valor": cad.get("capital_social"), "formato": "brl", "icone": "💼", "cor": theme.VERDE},
                {"rotulo": "Sede", "valor": f"{cad.get('municipio', '')}/{cad.get('uf', '')}", "formato": "txt",
                 "icone": "📍", "cor": theme.AMBAR},
            ])
            st.caption(f"CNAE principal: {cad.get('cnae_fiscal')} – {cad.get('cnae_fiscal_descricao')} · "
                       f"Situação: {cad.get('descricao_situacao_cadastral')} · "
                       f"Simples: {'sim' if cad.get('opcao_pelo_simples') else 'não'}")
            socios = cad.get("qsa") or []
            if socios:
                with st.expander(f"Quadro societário ({len(socios)})"):
                    grid(pd.DataFrame(socios), "socios", {"nome_socio": {"titulo": "Sócio", "tipo": "longo"},
                                                          "qualificacao_socio": {"titulo": "Qualificação", "largura": 220},
                                                          "data_entrada_sociedade": {"tipo": "data", "titulo": "Entrada", "largura": 120}},
                         selecao=False, busca=False)
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
            theme.kpis([
                {"rotulo": "Itens ganhos", "valor": len(its), "formato": "int", "icone": "🏆", "cor": theme.INDIGO},
                {"rotulo": "Valor homologado", "valor": its.valorTotalHomologado.sum(), "formato": "brl", "icone": "💰", "cor": theme.VERDE},
                {"rotulo": "Órgãos atendidos", "valor": its.orgaoEntidadeCnpj.nunique(), "formato": "int", "icone": "🏛", "cor": theme.CIANO},
                {"rotulo": "Desconto médio", "valor": pd.to_numeric(its.get("percentualDesconto"), errors="coerce").mean(),
                 "formato": "pct", "icone": "🏷", "cor": theme.AMBAR},
            ])
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
            r_sel, _ = grid(tab, "its_emp", {
                "dataResultadoPncp": {"tipo": "data", "titulo": "Resultado", "largura": 115, "fixa": True},
                "descricao": {"tipo": "longo", "titulo": "Descrição", "min": 300},
                "catmat": {"titulo": "CATMAT", "largura": 100},
                "unidade": {"titulo": "Un.", "largura": 100},
                "unidadeOrgaoUfSigla": {"titulo": "UF", "largura": 70},
                "quantidadeHomologada": {"tipo": "num", "titulo": "Qtd.", "largura": 95},
                "valorUnitarioHomologado": {"tipo": "brl", "titulo": "Unit.", "largura": 125},
                "valorTotalHomologado": {"tipo": "brl", "titulo": "Total", "largura": 135},
                "percentualDesconto": {"tipo": "pct", "titulo": "Desc.", "largura": 90},
                "aplicacaoBeneficioMeepp": {"titulo": "ME/EPP", "largura": 95},
                "idContratacaoPNCP": {"titulo": "Contratação PNCP", "largura": 230}})
            if its["descricao"].notna().any():
                top = its.dropna(subset=["descricao"]).assign(d=lambda x: x.descricao.str[:70]) \
                    .groupby("d").valorTotalHomologado.sum().nlargest(10).reset_index()
                st.plotly_chart(px.bar(top, x="valorTotalHomologado", y="d", orientation="h",
                                       title="Itens que mais faturaram").update_yaxes(autorange="reversed", title=""),
                                use_container_width=True)
            if r_sel is not None:
                st.session_state.edital_sel = r_sel["idContratacaoPNCP"]
                if st.button("📄 Abrir esta contratação (itens, descrição e edital)"):
                    st.switch_page("views/edital.py")
            st.download_button("⬇️ Exportar (CSV)", its.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                               f"itens_{cnpj}.csv", "text/csv")
