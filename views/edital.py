import pandas as pd
import streamlit as st

from core import pncp, storage, ia
from core.http import APIError
from core.ui import brl, id_de_link, aviso_api

cart = storage.carregar()

st.title("📄 Edital + análise com IA")

entrada = st.text_input("Número de controle PNCP ou link do edital",
                        value=st.session_state.get("edital_sel", ""),
                        placeholder="ex.: 83551515000107-1-000148/2026  ou  https://pncp.gov.br/app/editais/…")
pid = id_de_link(entrada)

aba_pncp, aba_upload = st.tabs(["🔗 Edital do PNCP", "⬆️ Enviar PDF próprio"])


def mostrar_analise(a: dict):
    nota = a.get("nota_viabilidade", 0)
    c = st.columns([1, 3])
    c[0].metric("Viabilidade", f"{nota}/10")
    c[1].info(a.get("justificativa_nota", ""))
    st.markdown(f"**Objeto:** {a.get('resumo_objeto', '')}")
    campos = [("Órgão", "orgao"), ("Modalidade / critério", "modalidade_e_criterio"),
              ("Sessão pública", "data_sessao_publica"), ("Prazo de propostas", "prazo_propostas"),
              ("Valor estimado", "valor_estimado"), ("Prazo de entrega", "prazo_entrega"),
              ("Local de entrega", "local_entrega"), ("Pagamento", "condicoes_pagamento"),
              ("Vigência", "vigencia"), ("Garantia contratual", "garantia_contratual"),
              ("Garantia do produto / assistência", "garantia_produto_assistencia"),
              ("Amostra / prova de conceito", "amostra_ou_prova_conceito"),
              ("Benefício ME/EPP", "beneficio_me_epp"),
              ("Consórcio / subcontratação", "permite_consorcio_subcontratacao")]
    st.dataframe(pd.DataFrame([(r, a.get(k, "")) for r, k in campos], columns=["Campo", "Edital"]),
                 hide_index=True, use_container_width=True)

    t = st.tabs(["✅ Habilitação", "⚠️ Atenção", "📦 Itens", "🗒️ Checklist", "{} JSON"])
    with t[0]:
        for titulo, k in [("Habilitação jurídica", "habilitacao_juridica"),
                          ("Regularidade fiscal e trabalhista", "regularidade_fiscal_trabalhista"),
                          ("Qualificação técnica", "qualificacao_tecnica"),
                          ("Qualificação econômico-financeira", "qualificacao_economico_financeira"),
                          ("Documentos da proposta", "documentos_proposta")]:
            st.markdown(f"**{titulo}**")
            for x in a.get(k, []) or ["—"]:
                st.checkbox(x, key=f"{titulo}-{x}")
    with t[1]:
        st.markdown("**Pontos de atenção**")
        for x in a.get("pontos_de_atencao", []):
            st.markdown(f"- {x}")
        st.markdown("**Cláusulas possivelmente restritivas** (base para esclarecimento/impugnação)")
        for x in a.get("clausulas_possivelmente_restritivas", []) or ["Nenhuma identificada."]:
            st.markdown(f"- {x}")
        st.markdown("**Penalidades**")
        for x in a.get("penalidades", []):
            st.markdown(f"- {x}")
    with t[2]:
        st.dataframe(pd.DataFrame(a.get("itens_principais", [])), hide_index=True, use_container_width=True)
    with t[3]:
        st.dataframe(pd.DataFrame(a.get("checklist", [])), hide_index=True, use_container_width=True)
    with t[4]:
        st.json(a)
    st.caption("⚖️ Análise automatizada para triagem. Confirme sempre no texto do edital antes de decidir ou impugnar.")


with aba_pncp:
    if not pid:
        st.info("Informe um edital acima, ou escolha um no **Radar de editais**.")
    else:
        try:
            with st.spinner("Carregando dados do PNCP…"):
                cab = pncp.contratacao(pid)
                its = pncp.itens(pid)
                arqs = pncp.arquivos(pid)
        except APIError as e:
            aviso_api(e); st.stop()

        if cab:
            st.subheader(cab.get("objetoCompra", "")[:300])
            u = cab.get("unidadeOrgao", {}) or {}
            k = st.columns(4)
            k[0].metric("Valor estimado", brl(cab.get("valorTotalEstimado")))
            k[1].metric("Modalidade", cab.get("modalidadeNome", "—"))
            fim = pd.to_datetime(cab.get("dataEncerramentoProposta"), errors="coerce")
            k[2].metric("Propostas até", fim.strftime("%d/%m %H:%M") if pd.notna(fim) else "—")
            k[3].metric("Itens", len(its))
            st.caption(f"Situação: {cab.get('situacaoCompraNome', '—')}")
            st.caption(f"{(cab.get('orgaoEntidade') or {}).get('razaoSocial', '')} · {u.get('nomeUnidade', '')} — "
                       f"{u.get('municipioNome', '')}/{u.get('ufSigla', '')} · SRP: {'sim' if cab.get('srp') else 'não'} · "
                       f"Amparo: {(cab.get('amparoLegal') or {}).get('nome', '—')}")
            if cab.get("linkSistemaOrigem"):
                st.link_button("Abrir no sistema de disputa ↗", cab["linkSistemaOrigem"])

        st.markdown("#### Itens")
        if its.empty:
            st.caption("Sem itens publicados.")
        else:
            ev = st.dataframe(its, hide_index=True, use_container_width=True, on_select="rerun",
                              selection_mode="single-row", key="itens_ed",
                              column_config={
                                  "valorUnitarioEstimado": st.column_config.NumberColumn("Vlr unit. estimado", format="R$ %.2f"),
                                  "valorTotal": st.column_config.NumberColumn("Vlr total", format="R$ %.2f"),
                                  "catalogoCodigoItem": "CATMAT/CATSER",
                                  "descricao": st.column_config.TextColumn("Descrição", width="large")})
            if ev.selection.rows:
                linha = its.iloc[ev.selection.rows[0]]
                c1, c2 = st.columns(2)
                if linha.get("catalogoCodigoItem") and c1.button("💰 Ver preço histórico deste item", use_container_width=True):
                    st.session_state.catmat_sel = str(linha["catalogoCodigoItem"])
                    st.session_state.catmat_servico = linha.get("materialOuServicoNome") == "Serviço"
                    st.switch_page("views/precos.py")
                if c2.button("🧮 Levar à calculadora (valor estimado)", use_container_width=True):
                    st.session_state.preco_ref = float(linha.get("valorUnitarioEstimado") or 0)
                    st.session_state.qtd_ref = float(linha.get("quantidade") or 1)
                    st.switch_page("views/calculadora.py")

        st.markdown("#### Documentos")
        if not arqs:
            st.caption("Nenhum arquivo publicado no PNCP. Use a aba **Enviar PDF próprio**.")
        else:
            docs = pd.DataFrame(arqs)[["titulo", "tipoDocumentoNome", "dataPublicacaoPncp", "url"]]
            st.dataframe(docs, hide_index=True, use_container_width=True,
                         column_config={"url": st.column_config.LinkColumn("Baixar", display_text="baixar ↓")})
            padrao = [a["titulo"] for a in arqs if a.get("tipoDocumentoId") in (2, 4)] or [arqs[0]["titulo"]]
            escolhidos = st.multiselect("Documentos para a IA analisar", [a["titulo"] for a in arqs], default=padrao)

            if pid in cart["analises"]:
                st.success("Este edital já tem análise salva.")
            col1, col2 = st.columns([1, 2])
            esforco = col2.select_slider("Profundidade", ["low", "medium", "high"], value="medium",
                                         help="Maior profundidade = análise mais cuidadosa, porém mais lenta e cara.")
            if col1.button("🤖 Analisar com IA", type="primary", use_container_width=True, disabled=not escolhidos):
                try:
                    with st.status("Lendo o edital…", expanded=True) as stt:
                        arquivos = []
                        for a in arqs:
                            if a["titulo"] in escolhidos:
                                st.write(f"Baixando {a['titulo']}…")
                                dados, _ = pncp.baixar_arquivo(a["url"])
                                arquivos.append((a["titulo"], dados))
                        st.write("Analisando exigências com Claude (1–3 min)…")
                        ctx = f"{pid}; objeto: {(cab or {}).get('objetoCompra', '')[:500]}"
                        res = ia.analisar(arquivos, ctx, esforco)
                        stt.update(label="Análise concluída", state="complete")
                    cart["analises"][pid] = res
                    meta = st.session_state.get("edital_meta") or {}
                    cart["salvos"].setdefault(pid, {**{k: str(v) for k, v in meta.items()},
                                                    "pncp_id": pid,
                                                    "objeto": (cab or {}).get("objetoCompra", "")})
                    storage.salvar()
                except (RuntimeError, APIError) as e:
                    st.error(str(e))
            if pid in cart["analises"]:
                st.divider()
                mostrar_analise(cart["analises"][pid])

with aba_upload:
    st.caption("Para editais fora do PNCP (portais estaduais/municipais, BLL, Licitações-e etc.).")
    up = st.file_uploader("Edital, TR e anexos (PDF, DOCX, ZIP)", type=["pdf", "docx", "zip", "txt"],
                          accept_multiple_files=True)
    nome = st.text_input("Identificação (ex.: PE 90012/2026 – Prefeitura X)")
    if st.button("🤖 Analisar arquivos enviados", disabled=not (up and nome)):
        try:
            with st.spinner("Analisando com Claude (1–3 min)…"):
                res = ia.analisar([(f.name, f.getvalue()) for f in up], nome)
            cart["analises"][nome] = res
            cart["salvos"].setdefault(nome, {"pncp_id": nome, "objeto": res.get("resumo_objeto", "")})
            storage.salvar()
            st.session_state.upload_res = nome
        except RuntimeError as e:
            st.error(str(e))
    if st.session_state.get("upload_res") in cart["analises"]:
        mostrar_analise(cart["analises"][st.session_state.upload_res])
