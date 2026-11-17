"""Persistência simples da "carteira": perfil da empresa, editais salvos e análises de IA.

Local: grava em data/carteira.json. No Streamlit Community Cloud o disco é efêmero
(apaga ao reiniciar), por isso a tela oferece exportar/importar o JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ARQ = Path(__file__).resolve().parent.parent / "data" / "carteira.json"

PADRAO = {
    "perfil": {
        "empresa": "",
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
