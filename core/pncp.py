"""Portal Nacional de Contratações Públicas (PNCP).

Endpoints usados (todos públicos, sem chave):
- Busca textual (a mesma do site):      https://pncp.gov.br/api/search/
- Itens de uma contratação:             /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens
- Resultado (vencedor) de um item:      .../itens/{n}/resultados
- Arquivos (edital, TR, anexos):        .../arquivos
- Contratação (detalhe):                /api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from .http import get_json, get_bytes, APIError

SEARCH = "https://pncp.gov.br/api/search/"
API = "https://pncp.gov.br/api/pncp/v1"
CONSULTA = "https://pncp.gov.br/api/consulta/v1"

MODALIDADES = {
    6: "Pregão Eletrônico",
    8: "Dispensa de Licitação",
    4: "Concorrência Eletrônica",
    7: "Pregão Presencial",
    5: "Concorrência Presencial",
    9: "Inexigibilidade",
    12: "Credenciamento",
    1: "Leilão Eletrônico",
    3: "Concurso",
    2: "Diálogo Competitivo",
}

UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
       "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]

STATUS = {
    "recebendo_proposta": "Recebendo propostas",
    "encerradas": "Encerradas",
    "todos": "Todos",
}


def _parse_dt(v):
    if not v:
        return pd.NaT
    try:
        return pd.to_datetime(v)
    except Exception:
        return pd.NaT


@st.cache_data(ttl=60 * 30, show_spinner=False)
def _pagina_busca(q: str, status: str, uf, mod, pagina: int, tam_pagina: int, tipo_documento: str) -> dict:
    """Uma página da busca. Cache individual: se outra consulta falhar, esta não se perde."""
    return get_json(SEARCH, {
        "q": q or "", "tipos_documento": tipo_documento, "ordenacao": "-data",
        "pagina": pagina, "tam_pagina": tam_pagina, "status": status,
        "ufs": uf, "modalidades": mod,
    }) or {}


def buscar_editais(q: str = "", status: str = "recebendo_proposta", ufs: tuple = (),
                   modalidades: tuple = (), paginas: int = 2, tam_pagina: int = 100,
                   tipo_documento: str = "edital", falhas: list | None = None) -> tuple[pd.DataFrame, int]:
    """Busca na base do PNCP. Consulta cada UF/modalidade separadamente (o filtro
    multi-valor do PNCP é instável). Falhas parciais vão para `falhas`; só levanta
    erro se TODAS as consultas falharem."""
    combos = [(u, m) for u in (ufs or (None,)) for m in (modalidades or (None,))]
    rows, total, erros = [], 0, []
    for uf, mod in combos:
        for pagina in range(1, paginas + 1):
            try:
                data = _pagina_busca(q, status, uf, mod, pagina, tam_pagina, tipo_documento)
            except APIError as e:
                erros.append((q, uf, MODALIDADES.get(mod, mod), str(e)))
                break
            items = data.get("items", [])
            if pagina == 1:
                total += int(data.get("total") or 0)
            rows.extend(items)
            if len(items) < tam_pagina:
                break
    if falhas is not None:
        falhas.extend(erros)
    if erros and len(erros) == len(combos):
        raise APIError(erros[0][3])
    return normalizar_busca(rows), total


def normalizar_busca(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).drop_duplicates("numero_controle_pncp")
    out = pd.DataFrame({
        "pncp_id": df["numero_controle_pncp"],
        "titulo": df.get("title"),
        "objeto": df.get("description"),
        "orgao": df.get("orgao_nome"),
        "orgao_cnpj": df.get("orgao_cnpj"),
        "unidade": df.get("unidade_nome"),
        "municipio": df.get("municipio_nome"),
        "uf": df.get("uf"),
        "esfera": df.get("esfera_nome"),
        "modalidade_id": pd.to_numeric(df.get("modalidade_licitacao_id"), errors="coerce"),
        "modalidade": df.get("modalidade_licitacao_nome"),
        "situacao": df.get("situacao_nome"),
        "srp": df.get("srp"),
        "valor_estimado": pd.to_numeric(df.get("valor_total_estimado"), errors="coerce"),
        "abertura_propostas": df.get("data_inicio_vigencia").map(_parse_dt),
        "fim_propostas": df.get("data_fim_vigencia").map(_parse_dt),
        "publicacao": df.get("data_publicacao_pncp").map(_parse_dt),
        "ano": df.get("ano"),
        "sequencial": df.get("numero_sequencial"),
        "item_url": df.get("item_url"),
        "link_origem": df.get("link_sistema_origem"),
        "info": df.get("informacao_complementar"),
    })
    out["link_pncp"] = "https://pncp.gov.br/app/editais/" + out["orgao_cnpj"].astype(str) + "/" \
        + out["ano"].astype(str) + "/" + out["sequencial"].astype(str)
    agora = pd.Timestamp(datetime.now())
    out["fase"] = "Aberto"
    out.loc[out["abertura_propostas"] > agora, "fase"] = "A abrir"
    out.loc[out["fim_propostas"] < agora, "fase"] = "Encerrado"
    out["dias_para_fim"] = (out["fim_propostas"] - agora).dt.total_seconds() / 86400
    return out.reset_index(drop=True)


def _parse_id(pncp_id: str) -> tuple[str, str, str]:
    """'83551515000107-1-000148/2026' -> (cnpj, ano, sequencial)."""
    cnpj, _, resto = pncp_id.split("-", 2)
    seq, ano = resto.split("/")
    return cnpj, ano, str(int(seq))


@st.cache_data(ttl=60 * 60, show_spinner=False)
def itens(pncp_id: str) -> pd.DataFrame:
    cnpj, ano, seq = _parse_id(pncp_id)
    rows, pagina = [], 1
    while True:
        data = get_json(f"{API}/orgaos/{cnpj}/compras/{ano}/{seq}/itens",
                        {"pagina": pagina, "tamanhoPagina": 500}) or []
        rows.extend(data)
        if len(data) < 500:
            break
        pagina += 1
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    keep = ["numeroItem", "descricao", "catalogoCodigoItem", "quantidade", "unidadeMedida",
            "valorUnitarioEstimado", "valorTotal", "tipoBeneficioNome", "criterioJulgamentoNome",
            "situacaoCompraItemNome", "materialOuServicoNome", "orcamentoSigiloso", "temResultado"]
    return df[[c for c in keep if c in df.columns]]


@st.cache_data(ttl=60 * 60, show_spinner=False)
def resultados_item(pncp_id: str, numero_item: int) -> list[dict]:
    cnpj, ano, seq = _parse_id(pncp_id)
    return get_json(f"{API}/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{numero_item}/resultados") or []


@st.cache_data(ttl=60 * 60, show_spinner=False)
def arquivos(pncp_id: str) -> list[dict]:
    cnpj, ano, seq = _parse_id(pncp_id)
    return get_json(f"{API}/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos") or []


@st.cache_data(ttl=60 * 60, show_spinner=False)
def contratacao(pncp_id: str) -> dict:
    cnpj, ano, seq = _parse_id(pncp_id)
    return get_json(f"{CONSULTA}/orgaos/{cnpj}/compras/{ano}/{seq}") or {}


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False, max_entries=20)
def baixar_arquivo(url: str) -> tuple[bytes, str]:
    return get_bytes(url)
