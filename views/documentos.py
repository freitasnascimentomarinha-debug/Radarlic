import pandas as pd
import streamlit as st

from core import pncp, storage, theme, docs, ia
from core.grid import grid
from core.http import APIError
from core.ui import brl, id_de_link, aviso_api

cart = storage.carregar()
perfil = cart["perfil"]
theme.hero("📝", "Proposta e petições",
           "Gere a <b>proposta comercial</b> em Word a partir dos itens do edital e redija <b>pedido de esclarecimento</b> "
           "ou <b>impugnação</b> com IA, usando a análise do edital.")

if not perfil.get("empresa") or not perfil.get("cnpj"):
    st.warning("Preencha razão social, CNPJ, endereço e dados bancários em **Meu perfil** — eles entram nos documentos.")

opcoes = list(cart["salvos"])
padrao = st.session_state.get("edital_sel")
c1, c2 = st.columns([2, 1])
escolha = c1.selectbox("Edital da carteira", [""] + opcoes,
                       index=(opcoes.index(padrao) + 1) if padrao in opcoes else 0,
                       format_func=lambda p: p and f"{p} — {(cart['salvos'][p].get('objeto') or '')[:70]}" or "—")
manual = c2.text_input("…ou número/link PNCP", value="" if escolha else (padrao or ""))
pid = escolha or id_de_link(manual)
if not pid:
    st.stop()
meta = cart["salvos"].get(pid, {"pncp_id": pid})

aba_prop, aba_pet = st.tabs(["📄 Proposta comercial", "⚖️ Esclarecimento / impugnação"])

with aba_prop:
    try:
        with st.spinner("Carregando itens do PNCP…"):
            its = pncp.itens(pid)
            cab = pncp.contratacao(pid)
    except APIError as e:
        aviso_api(e); its, cab = pd.DataFrame(), {}
    if cab:
        meta = {**meta, "orgao": meta.get("orgao") or (cab.get("orgaoEntidade") or {}).get("razaoSocial"),
                "objeto": meta.get("objeto") or cab.get("objetoCompra"),
                "titulo": meta.get("titulo") or f"{cab.get('modalidadeNome', '')} nº {cab.get('numeroCompra', '')}/{cab.get('anoCompra', '')}"}
    if its.empty:
        st.info("Sem itens no PNCP para este edital.")
    else:
        tab = pd.DataFrame({
            "incluir": False, "item": its["numeroItem"], "descricao": its["descricao"].str[:300],
            "unidade": its.get("unidadeMedida"), "quantidade": its["quantidade"],
            "estimado": its.get("valorUnitarioEstimado"), "valor_unitario": its.get("valorUnitarioEstimado"),
            "marca": "", "modelo": ""})
        st.caption("Marque os itens que vai cotar e preencha **valor unitário, marca e modelo** (células amarelas).")
        _, ed = grid(tab, f"prop_{pid}", {
            "incluir": {"titulo": "Cotar?", "editavel": True, "largura": 90, "fixa": True},
            "item": {"titulo": "Item", "largura": 70},
            "descricao": {"tipo": "longo", "titulo": "Descrição", "min": 300},
            "unidade": {"titulo": "Un.", "largura": 90}, "quantidade": {"tipo": "num", "titulo": "Qtd.", "largura": 90},
            "estimado": {"tipo": "brl", "titulo": "Estimado (un.)", "largura": 130},
            "valor_unitario": {"tipo": "brl", "titulo": "Meu preço (un.)", "editavel": True, "largura": 140},
            "marca": {"titulo": "Marca", "editavel": True, "largura": 130},
            "modelo": {"titulo": "Modelo", "editavel": True, "largura": 130},
        }, editavel=True, selecao=False, pagina=50)
        ed = tab.assign(**{c: ed[c] for c in ("incluir", "valor_unitario", "marca", "modelo")})
        ed["incluir"] = ed["incluir"].map(lambda v: v is True or str(v).lower() in ("true", "1", "sim", "x"))
        sel = ed[ed.incluir]
        a = analise = cart["analises"].get(pid, {})
        c1, c2, c3 = st.columns(3)
        validade = c1.number_input("Validade da proposta (dias)", 30, 180, 60)
        prazo = c2.text_input("Prazo de entrega", a.get("prazo_entrega", "") if a else "")
        local = c3.text_input("Local de entrega", a.get("local_entrega", "") if a else "")
        total = (pd.to_numeric(sel.valor_unitario, errors="coerce") * sel.quantidade).sum()
        st.markdown(f"**{len(sel)} item(ns) selecionado(s) · valor global {brl(total)}**")
        if len(sel):
            st.download_button("⬇️ Baixar proposta (.docx)", docs.proposta_docx(perfil, meta, sel, validade, prazo, local),
                               f"proposta_{pid.replace('/', '-')}.docx", type="primary",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            if st.button("Registrar valor no funil"):
                storage.salvar_edital(pid, meta)
                cart["salvos"][pid].update(valor_proposta=float(total), status="Proposta enviada")
                storage.salvar(); st.toast("Funil atualizado: Proposta enviada.", icon="📤")

with aba_pet:
    analise = cart["analises"].get(pid)
    if not analise:
        st.info("Primeiro analise este edital com IA em **Edital + análise IA** — a petição usa essa análise.")
        st.stop()
    tipo = st.radio("Tipo", ["Pedido de esclarecimento", "Impugnação ao edital"], horizontal=True,
                    help="Prazo: até 3 dias úteis antes da abertura da sessão (art. 164 da Lei 14.133/2021).")
    sugestoes = (analise.get("clausulas_possivelmente_restritivas") or []) + (analise.get("pontos_de_atencao") or [])
    pontos = st.multiselect("Pontos a questionar (sugeridos pela análise)", sugestoes,
                            default=(analise.get("clausulas_possivelmente_restritivas") or [])[:3])
    extra = st.text_area("Outros pontos ou observações")
    if extra:
        pontos = pontos + [extra]
    chave = f"pet_{pid}_{tipo}"
    if st.button("🤖 Redigir com IA", type="primary", disabled=not pontos or not ia.ia_configurada(),
                 help=None if ia.ia_configurada() else "Configure ANTHROPIC_API_KEY nas Secrets."):
        try:
            with st.spinner("Redigindo (≈1 min)…"):
                st.session_state[chave] = ia.redigir_peticao(tipo, analise, pontos, perfil, pid)
        except RuntimeError as e:
            st.error(str(e))
    if chave in st.session_state:
        texto = st.text_area("Texto (edite à vontade)", st.session_state[chave], height=420)
        dest = f"Ao(À) Agente de Contratação/Pregoeiro(a) — {analise.get('orgao', '')}"
        st.download_button("⬇️ Baixar (.docx)", docs.peticao_docx(perfil, tipo, dest, texto),
                           f"{'esclarecimento' if 'esclarec' in tipo.lower() else 'impugnacao'}_{pid.replace('/', '-')}.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        st.caption("⚖️ Minuta gerada por IA: revise fundamentos e fatos antes de protocolar.")
