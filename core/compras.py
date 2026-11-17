"""API de Dados Abertos do Compras.gov.br (https://dadosabertos.compras.gov.br/swagger-ui/index.html).

- Preços praticados por CATMAT/CATSER   (03 - Pesquisa de Preço)
- Catálogo de materiais                 (modulo-material)
- Resultados de itens (vencedores)      (07 - Contratações, Lei 14.133)
- Plano de Contratações Anual (PCA)     (04 - PGC) -> compras FUTURAS planejadas
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import date

import pandas as pd
import streamlit as st

from .http import get_json, APIError
from . import pncp

BASE = "https://dadosabertos.compras.gov.br"


def _paginar(path: str, params: dict, max_paginas: int = 10, tam: int = 500) -> list[dict]:
    rows = []
    for pagina in range(1, max_paginas + 1):
        data = get_json(f"{BASE}{path}", {**params, "pagina": pagina, "tamanhoPagina": tam}) or {}
        res = data.get("resultado") or []
        rows.extend(res)
        if not data.get("paginasRestantes"):
            break
    return rows


# ---------------------------------------------------------------- catálogo
@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def item_catmat(codigo: int) -> dict:
    data = get_json(f"{BASE}/modulo-material/4_consultarItemMaterial",
                    {"pagina": 1, "tamanhoPagina": 10, "codigoItem": codigo}) or {}
    res = data.get("resultado") or []
    return res[0] if res else {}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def descobrir_catmat(texto: str, max_editais: int = 20) -> pd.DataFrame:
    """A API oficial não tem busca textual no catálogo. Estratégia: busca o termo nos
    editais do PNCP, lê os itens dessas compras e coleta os códigos CATMAT/CATSER
    (catalogoCodigoItem) cujas descrições contêm as palavras pesquisadas."""
    termos = [t for t in _norm(texto).split() if len(t) > 2]
    df, _ = pncp.buscar_editais(q=texto, status="todos", paginas=1, tam_pagina=max_editais)
    cont, exemplos, unidades = Counter(), {}, {}
    for pid in df.get("pncp_id", pd.Series(dtype=str)).head(max_editais):
        try:
            its = pncp.itens(pid)
        except APIError:
            continue
        if its.empty or "catalogoCodigoItem" not in its:
            continue
        for _, r in its.iterrows():
            cod = r.get("catalogoCodigoItem")
            desc = _norm(str(r.get("descricao", "")))
            if cod and all(t in desc for t in termos):
                cont[str(cod)] += 1
                exemplos.setdefault(str(cod), str(r.get("descricao", ""))[:160])
                unidades.setdefault(str(cod), r.get("unidadeMedida"))
    if not cont:
        return pd.DataFrame(columns=["codigo", "ocorrencias", "descricao", "unidade"])
    return pd.DataFrame([
        {"codigo": c, "ocorrencias": n, "descricao": exemplos[c], "unidade": unidades[c]}
        for c, n in cont.most_common(20)
    ])


# ---------------------------------------------------------------- preços praticados
@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def precos_praticados(codigo: str, servico: bool = False, uf: str | None = None,
                      inicio: date | None = None, fim: date | None = None,
                      max_paginas: int = 6) -> pd.DataFrame:
    if servico:
        path = "/modulo-pesquisa-preco/3_consultarServico"
        params = {"codigoItemCatalogo": codigo}
    else:
        path = "/modulo-pesquisa-preco/1_consultarMaterial"
        params = {"tipo": "codigoItemCatalogo", "codigo": codigo}
    params.update({
        "estado": uf,
        "dataCompraInicio": inicio.isoformat() if inicio else None,
        "dataCompraFim": fim.isoformat() if fim else None,
    })
    rows = _paginar(path, params, max_paginas=max_paginas)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["dataCompra"] = pd.to_datetime(df.get("dataCompra"), errors="coerce")
    df["precoUnitario"] = pd.to_numeric(df.get("precoUnitario"), errors="coerce")
    df["quantidade"] = pd.to_numeric(df.get("quantidade"), errors="coerce")
    if "capacidadeUnidadeFornecimento" in df:
        cap = pd.to_numeric(df["capacidadeUnidadeFornecimento"], errors="coerce")
        df["unidade_fornecimento"] = df.get("siglaUnidadeFornecimento", "").astype(str) + \
            cap.map(lambda x: f" c/ {x:g}" if pd.notna(x) and x not in (0, 1) else "")
    else:
        df["unidade_fornecimento"] = df.get("siglaUnidadeFornecimento", "UN")
    return df.dropna(subset=["precoUnitario"])


def estatisticas(df: pd.DataFrame, remover_outliers: bool = True) -> tuple[dict, pd.DataFrame]:
    """Estatísticas de preço. O corte de outliers segue a lógica do art. 6º da IN SEGES 65/2021
    (desconsiderar preços inexequíveis ou excessivamente elevados) usando o intervalo IQR."""
    s = df["precoUnitario"]
    base = df
    if remover_outliers and len(s) >= 5:
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        base = df[(s >= q1 - 1.5 * iqr) & (s <= q3 + 1.5 * iqr)]
    p = base["precoUnitario"]
    mensal = (base.set_index("dataCompra")["precoUnitario"]
              .resample("MS").agg(["min", "mean", "max", "count"]).dropna())
    stats = {
        "n": int(len(p)), "descartados": int(len(df) - len(base)),
        "media": p.mean(), "mediana": p.median(), "minimo": p.min(), "maximo": p.max(),
        "media_minimos": mensal["min"].mean() if not mensal.empty else None,
        "media_maximos": mensal["max"].mean() if not mensal.empty else None,
        "p25": p.quantile(0.25), "p75": p.quantile(0.75),
        "cv": (p.std() / p.mean()) if p.mean() else None,
    }
    return stats, mensal


# ---------------------------------------------------------------- vencedores / concorrentes
@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def itens_vencidos_fornecedor(cnpj: str, inicio: date, fim: date, max_paginas: int = 10) -> pd.DataFrame:
    """Todos os itens homologados para um fornecedor (Lei 14.133, via PNCP)."""
    rows = _paginar("/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133", {
        "niFornecedor": re.sub(r"\D", "", cnpj),
        "dataResultadoPncpInicial": inicio.isoformat(),
        "dataResultadoPncpFinal": fim.isoformat(),
    }, max_paginas=max_paginas)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for c in ("valorUnitarioHomologado", "valorTotalHomologado", "quantidadeHomologada"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["dataResultadoPncp"] = pd.to_datetime(df.get("dataResultadoPncp"), errors="coerce")
    return df


# ---------------------------------------------------------------- PCA (compras futuras)
@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def pca_por_classe(codigo_classe: int, ano: int, servico: bool = False, max_paginas: int = 6) -> pd.DataFrame:
    rows = _paginar("/modulo-pgc/2_consultarPgcDetalheCatalogo", {
        "anoPcaProjetoCompra": ano, "tipo": "Servico" if servico else "Material", "codigo": codigo_classe,
    }, max_paginas=max_paginas)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for c in ("quantidadeItem", "valorUnitarioItem", "valorTotalItem"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["dataPrevistaFormalizacaoDemanda"] = pd.to_datetime(df.get("dataPrevistaFormalizacaoDemanda"), errors="coerce")
    return df
