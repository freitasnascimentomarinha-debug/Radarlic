"""Persistência simples da "carteira": perfil da empresa, editais salvos e análises de IA.

Local: grava em data/carteira.json. No Streamlit Community Cloud o disco é efêmero
(apaga ao reiniciar), por isso a tela oferece exportar/importar o JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ARQ = Path(__file__).resolve().parent.parent / "data" / "carteira.json"

STATUS_FUNIL = ["Triagem", "Cotando", "Proposta enviada", "Em disputa", "Ganho", "Perdido", "Desistência"]
CORES_FUNIL = {"Triagem": "#64748b", "Cotando": "#0891b2", "Proposta enviada": "#4f46e5",
               "Em disputa": "#d97706", "Ganho": "#059669", "Perdido": "#e11d48", "Desistência": "#94a3b8"}

# Documentos de habilitação mais pedidos (arts. 62 a 69 da Lei 14.133/2021)
CERTIDOES_PADRAO = [
    {"documento": "CND Federal (Receita/PGFN) – tributos federais e dívida ativa", "orgao": "Receita Federal",
     "link": "https://solucoes.receita.fazenda.gov.br/Servicos/certidaointernet/PJ/Emitir", "validade": None},
    {"documento": "CRF – Regularidade do FGTS", "orgao": "Caixa",
     "link": "https://consulta-crf.caixa.gov.br/consultacrf/pages/consultaEmpregador.jsf", "validade": None},
    {"documento": "CNDT – Débitos Trabalhistas", "orgao": "TST",
     "link": "https://cndt-certidao.tst.jus.br/inicio.faces", "validade": None},
    {"documento": "Certidão Negativa Estadual (ICMS)", "orgao": "SEFAZ do estado", "link": "", "validade": None},
    {"documento": "Certidão Negativa Municipal (ISS/IPTU)", "orgao": "Prefeitura", "link": "", "validade": None},
    {"documento": "Certidão de Falência e Recuperação Judicial", "orgao": "Tribunal de Justiça", "link": "", "validade": None},
    {"documento": "Balanço patrimonial do último exercício", "orgao": "Contabilidade", "link": "", "validade": None},
    {"documento": "SICAF – níveis cadastrais", "orgao": "Compras.gov.br",
     "link": "https://www.gov.br/compras/pt-br/sistemas/conheca-o-compras/sicaf-digital", "validade": None},
    {"documento": "Consulta CEIS/CNEP (sem sanções)", "orgao": "CGU – Portal da Transparência",
     "link": "https://portaldatransparencia.gov.br/sancoes/consulta", "validade": None},
]

PADRAO = {
    "perfil": {
        "empresa": "",
        "cnpj": "",
        "endereco": "",
        "telefone": "",
        "email": "",
        "banco": "",
        "responsavel": "",
        "cargo": "Sócio-administrador",
        "palavras": ["papel", "toner", "material de expediente"],
        "ufs": ["RJ"],
        "uf_sede": "RJ",
        "me_epp": True,
        "valor_min": 0.0,
        "valor_max": 500000.0,
        "catmats": [],
    },
    "salvos": {},      # pncp_id -> linha do edital (dict)
    "analises": {},    # pncp_id -> resultado da IA (dict)
    "certidoes": CERTIDOES_PADRAO,
}


def carregar() -> dict:
    if "carteira" not in st.session_state:
        dados = json.loads(json.dumps(PADRAO))
        try:
            if ARQ.exists():
                disk = json.loads(ARQ.read_text("utf-8"))
                for k in dados:
                    if k in disk:
                        dados[k] = disk[k] if k != "perfil" else {**dados[k], **disk[k]}
        except Exception:
            pass
        st.session_state.carteira = dados
    return st.session_state.carteira


def salvar() -> None:
    try:
        ARQ.parent.mkdir(exist_ok=True)
        ARQ.write_text(json.dumps(st.session_state.carteira, ensure_ascii=False, indent=2, default=str), "utf-8")
    except Exception:
        pass  # disco somente-leitura: segue só na sessão


def exportar() -> bytes:
    return json.dumps(carregar(), ensure_ascii=False, indent=2, default=str).encode("utf-8")


def importar(conteudo: bytes) -> None:
    dados = json.loads(conteudo.decode("utf-8"))
    base = json.loads(json.dumps(PADRAO))
    base.update({k: dados[k] for k in base if k in dados})
    st.session_state.carteira = base
    salvar()


def salvar_edital(pid: str, dados: dict) -> None:
    """Inclui/atualiza um edital na carteira, preservando status do funil e anotações."""
    import pandas as pd
    cart = carregar()
    limpo = {k: (v.isoformat() if isinstance(v, pd.Timestamp) else None if (isinstance(v, float) and v != v) else v)
             for k, v in dados.items()}
    atual = cart["salvos"].get(pid, {})
    cart["salvos"][pid] = {**limpo, **{k: atual[k] for k in ("status", "valor_proposta", "responsavel", "obs")
                                       if k in atual}}
    cart["salvos"][pid].setdefault("status", "Triagem")
    cart["salvos"][pid]["pncp_id"] = pid
    salvar()
