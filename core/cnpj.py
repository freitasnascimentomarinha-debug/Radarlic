"""Dados cadastrais de CNPJ (concorrentes) via BrasilAPI (espelho público da base da Receita)."""
from __future__ import annotations

import re

import streamlit as st

from .http import get_json, APIError


@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def consultar(cnpj: str) -> dict:
    cnpj = re.sub(r"\D", "", cnpj or "")
    if len(cnpj) != 14:
        return {}
    try:
        return get_json(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}", retries=2) or {}
    except APIError:
        return {}


def formatar(cnpj: str) -> str:
    c = re.sub(r"\D", "", cnpj or "")
    if len(c) != 14:
        return cnpj or ""
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
