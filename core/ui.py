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


def tabela_editais(df: pd.DataFrame, key: str, com_score: bool = True):
    """Mostra editais com seleção de linha. Retorna a linha selecionada (Series) ou None."""
    if df.empty:
        st.info("Nenhum edital encontrado com esses filtros.")
        return None
    cols = (["score"] if com_score and "score" in df else []) + [
        "fase", "fim_propostas", "objeto", "orgao", "municipio", "uf", "modalidade",
        "valor_estimado", "motivos", "link_pncp"]
    cols = [c for c in cols if c in df.columns]
    ev = st.dataframe(
        df[cols], key=key, hide_index=True, use_container_width=True,
        on_select="rerun", selection_mode="single-row",
        column_config={
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
            "fase": "Fase",
            "fim_propostas": st.column_config.DatetimeColumn("Propostas até", format="DD/MM/YY HH:mm"),
            "objeto": st.column_config.TextColumn("Objeto", width="large"),
            "orgao": "Órgão", "municipio": "Município", "uf": "UF", "modalidade": "Modalidade",
            "valor_estimado": st.column_config.NumberColumn("Valor estimado", format="R$ %.2f"),
            "motivos": "Por que pontuou",
            "link_pncp": st.column_config.LinkColumn("PNCP", display_text="abrir ↗"),
        },
    )
    rows = ev.selection.rows if ev and ev.selection else []
    return df.iloc[rows[0]] if rows else None
