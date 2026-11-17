import pandas as pd
import streamlit as st

from core import pncp, storage, ia, theme
from core.grid import grid
from core.http import APIError
from core.ui import brl, id_de_link, aviso_api

cart = storage.carregar()

theme.hero("📄", "Edital + análise com IA",
           "Itens, documentos e — com um clique — a leitura completa do edital pela IA: exigências de habilitação, "
           "prazos, riscos, cláusulas restritivas e checklist.")

entrada = st.text_input("Número de controle PNCP ou link do edital",
                        value=st.session_state.get("edital_sel", ""),
                        placeholder="ex.: 83551515000107-1-000148/2026  ou  https://pncp.gov.br/app/editais/…")
pid = id_de_link(entrada)

aba_pncp, aba_upload = st.tabs(["🔗 Edital do PNCP", "⬆️ Enviar PDF próprio"])


def mostrar_analise(a: dict):
    nota = a.get("nota_viabilidade", 0) or 0
    cor = theme.VERDE if nota >= 7 else theme.AMBAR if nota >= 4 else theme.ROSA
    st.markdown(f"<div class='rl-card' style='display:flex;gap:18px;align-items:center'>"
                f"<div style='width:74px;height:74px;border-radius:50%;flex:none;display:grid;place-items:center;"
                f"background:conic-gradient({cor} {nota * 36}deg,#eef2f7 0);'><div style='width:58px;height:58px;"
                f"border-radius:50%;background:#fff;display:grid;place-items:center;font-weight:800;font-size:1.2rem;"
                f"color:{cor}'>{nota}/10</div></div><div><div class='t'>Viabilidade de participação</div>"
                f"<div class='s'>{a.get('justificativa_nota', '')}</div></div></div>", unsafe_allow_html=True)
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
    grid(pd.DataFrame([(r, a.get(k, "")) for r, k in campos], columns=["Campo", "Edital"]), f"campos_{id(a)}",
         {"Campo": {"largura": 230, "fixa": True}, "Edital": {"tipo": "longo", "min": 400}},
         selecao=False, busca=False, pagina=50)

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
        grid(pd.DataFrame(a.get("itens_principais", [])), f"ia_itens_{id(a)}",
             {"item": {"largura": 80}, "descricao": {"tipo": "longo"}, "quantidade": {"largura": 110},
              "unidade": {"largura": 110}, "valor_unitario_estimado": {"titulo": "valor unit.", "largura": 140}},
             selecao=False)
    with t[3]:
        grid(pd.DataFrame(a.get("checklist", [])), f"ia_check_{id(a)}",
             {"tarefa": {"tipo": "longo", "titulo": "Tarefa"}, "prazo": {"titulo": "Prazo", "largura": 220}},
             selecao=False, busca=False)
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
            fim = pd.to_datetime(cab.get("dataEncerramentoProposta"), errors="coerce")
            theme.kpis([
                {"rotulo": "Valor estimado", "valor": cab.get("valorTotalEstimado"), "formato": "brl", "icone": "💰", "cor": theme.VERDE},
                {"rotulo": "Modalidade", "valor": cab.get("modalidadeNome", "—"), "formato": "txt", "icone": "⚖", "cor": theme.INDIGO,
                 "sub": cab.get("situacaoCompraNome", "")},
                {"rotulo": "Propostas até", "valor": fim.strftime("%d/%m %H:%M") if pd.notna(fim) else "—", "formato": "txt",
                 "icone": "⏱", "cor": theme.ROSA},
                {"rotulo": "Itens", "valor": len(its), "formato": "int", "icone": "📦", "cor": theme.CIANO},
            ])
            if st.button("⭐ Salvar no funil"):
                storage.salvar_edital(pid, {**(st.session_state.get("edital_meta") or {}), "objeto": cab.get("objetoCompra"),
                                            "orgao": (cab.get("orgaoEntidade") or {}).get("razaoSocial"), "uf": u.get("ufSigla"),
                                            "fim_propostas": cab.get("dataEncerramentoProposta"),
                                            "valor_estimado": cab.get("valorTotalEstimado")})
                st.toast("Salvo no funil.", icon="⭐")
            st.caption(f"{(cab.get('orgaoEntidade') or {}).get('razaoSocial', '')} · {u.get('nomeUnidade', '')} — "
                       f"{u.get('municipioNome', '')}/{u.get('ufSigla', '')} · SRP: {'sim' if cab.get('srp') else 'não'} · "
                       f"Amparo: {(cab.get('amparoLegal') or {}).get('nome', '—')}")
            if cab.get("linkSistemaOrigem"):
                st.link_button("Abrir no sistema de disputa ↗", cab["linkSistemaOrigem"])

        st.markdown("#### Itens")
        if its.empty:
            st.caption("Sem itens publicados.")
        else:
            st.caption("Clique num item para ver o preço histórico ou levá-lo à calculadora.")
            linha, _ = grid(its, f"itens_{pid}", {
                "numeroItem": {"titulo": "Item", "largura": 75, "fixa": True},
                "descricao": {"tipo": "longo", "titulo": "Descrição", "min": 340},
                "catalogoCodigoItem": {"titulo": "CATMAT/CATSER", "largura": 130},
                "quantidade": {"tipo": "num", "titulo": "Qtd.", "largura": 95},
                "unidadeMedida": {"titulo": "Unidade", "largura": 110},
                "valorUnitarioEstimado": {"tipo": "brl", "titulo": "Unit. estimado", "largura": 140},
                "valorTotal": {"tipo": "brl", "titulo": "Total", "largura": 140},
                "tipoBeneficioNome": {"tipo": "badge", "titulo": "Benefício", "largura": 230,
                                      "cores": {"Participação exclusiva para ME/EPP": theme.VERDE, "Sem benefício": theme.CINZA}},
                "criterioJulgamentoNome": {"titulo": "Critério", "largura": 130},
                "situacaoCompraItemNome": {"tipo": "badge", "titulo": "Situação", "largura": 130,
                                           "cores": {"Em andamento": theme.INDIGO, "Homologado": theme.VERDE}},
            })
            if linha is not None:
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
            grid(pd.DataFrame(arqs), f"arqs_{pid}", {
                "titulo": {"tipo": "longo", "titulo": "Arquivo"},
                "tipoDocumentoNome": {"tipo": "badge", "titulo": "Tipo", "largura": 190,
                                      "cores": {"Edital": theme.INDIGO, "Termo de Referência": theme.VIOLETA}},
                "dataPublicacaoPncp": {"tipo": "datahora", "titulo": "Publicado", "largura": 150},
                "url": {"tipo": "link", "titulo": "Baixar"}}, selecao=False, busca=False)
            padrao = [a["titulo"] for a in arqs if a.get("tipoDocumentoId") in (2, 4)] or [arqs[0]["titulo"]]
            escolhidos = st.multiselect("Documentos para a IA analisar", [a["titulo"] for a in arqs], default=padrao)

            if pid in cart["analises"]:
                st.success("Este edital já tem análise salva.")
            col1, col2 = st.columns([1, 2])
            esforco = col2.select_slider("Profundidade", ["low", "medium", "high"], value="medium",
                                         help="Maior profundidade = análise mais cuidadosa, porém mais lenta e cara.")
            if not ia.ia_configurada():
                st.warning("Para a análise com IA, configure `ANTHROPIC_API_KEY` em Secrets (veja o README).")
            if col1.button("🤖 Analisar com IA", type="primary", use_container_width=True,
                           disabled=not escolhidos or not ia.ia_configurada()):
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
                    storage.salvar_edital(pid, {**meta, "objeto": meta.get("objeto") or (cab or {}).get("objetoCompra", ""),
                                                "fim_propostas": meta.get("fim_propostas") or (cab or {}).get("dataEncerramentoProposta")})
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
            storage.salvar_edital(nome, {"objeto": res.get("resumo_objeto", ""), "orgao": res.get("orgao", "")})
            st.session_state.upload_res = nome
        except RuntimeError as e:
            st.error(str(e))
    if st.session_state.get("upload_res") in cart["analises"]:
        mostrar_analise(cart["analises"][st.session_state.upload_res])
