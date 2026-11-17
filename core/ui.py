"""Utilitários de interface compartilhados."""
from __future__ import annotations

import math
import re

import pandas as pd
import streamlit as st


def brl(v, casas: int = 2) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    s = f"{v:,.{casas}f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, casas: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{casas}f}%".replace(".", ",")


def id_de_link(texto: str) -> str | None:
    """Aceita o número de controle PNCP ou o link do edital no portal."""
    texto = (texto or "").strip()
    m = re.search(r"(\d{14})-\d-(\d{6})/(\d{4})", texto)
    if m:
        return m.group(0)
    m = re.search(r"editais/(\d{14})/(\d{4})/(\d+)", texto)
    if m:
        cnpj, ano, seq = m.groups()
        return f"{cnpj}-1-{int(seq):06d}/{ano}"
    return None


def aviso_api(e: Exception):
    st.warning(
        "As APIs do governo (PNCP / Compras.gov.br) não responderam agora. Elas oscilam bastante; "
        f"tente de novo em alguns instantes.\n\nDetalhe técnico: `{e}`", icon="📡")


CORES_FASE = {"Aberto": "#059669", "A abrir": "#4f46e5", "Encerrado": "#94a3b8"}
CORES_MOD = {"Pregão - Eletrônico": "#4f46e5", "Dispensa": "#0891b2", "Concorrência - Eletrônica": "#7c3aed",
             "Pregão - Presencial": "#6366f1", "Concorrência - Presencial": "#8b5cf6", "Inexigibilidade": "#64748b",
             "Credenciamento": "#d97706", "Leilão - Eletrônico": "#e11d48"}


def tabela_editais(df: pd.DataFrame, key: str, com_score: bool = True):
    """Editais em AG Grid com seleção de linha. Retorna a linha selecionada (Series) ou None."""
    from .grid import grid
    if df.empty:
        st.info("Nenhum edital encontrado com esses filtros.")
        return None
    cols = {}
    if com_score and "score" in df:
        cols["score"] = {"tipo": "score", "titulo": "Score", "fixa": True, "largura": 140}
    cols.update({
        "fase": {"tipo": "badge", "titulo": "Fase", "cores": CORES_FASE, "largura": 110},
        "fim_propostas": {"tipo": "prazo", "titulo": "Propostas até"},
        "objeto": {"tipo": "longo", "titulo": "Objeto", "min": 320},
        "orgao": {"titulo": "Órgão", "largura": 220},
        "municipio": {"titulo": "Município", "largura": 140},
        "uf": {"titulo": "UF", "largura": 70},
        "modalidade": {"tipo": "badge", "titulo": "Modalidade", "cores": CORES_MOD, "largura": 190},
        "valor_estimado": {"tipo": "brl", "titulo": "Valor estimado", "largura": 150},
        "motivos": {"tipo": "longo", "titulo": "Por que pontuou", "min": 220, "flex": 1},
        "link_pncp": {"tipo": "link", "titulo": "PNCP"},
    })
    linha, _ = grid(df, key, cols)
    return linha
