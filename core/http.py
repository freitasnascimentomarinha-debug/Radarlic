"""Cliente HTTP resiliente para as APIs públicas (PNCP e Compras.gov.br).

As APIs do governo oscilam muito: respostas vazias, 500 intermitente, lentidão
(>50 s) e limitação de taxa. Por isso todo acesso passa por aqui, com retentativa
exponencial e timeout generoso.
"""
from __future__ import annotations

import time
from typing import Any

import requests

UA = "RadarLic/1.0 (monitoramento de compras publicas; dados abertos)"

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept": "application/json"})


class APIError(RuntimeError):
    pass


def get_json(url: str, params: dict | None = None, *, timeout: int = 60,
             retries: int = 4, backoff: float = 2.0) -> Any:
    """GET com retentativas. Retorna o JSON ou None quando a API responde 204/404 sem dados."""
    params = {k: v for k, v in (params or {}).items() if v not in (None, "", [])}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            if r.status_code == 204:
                return None
            if r.status_code == 404:
                # Compras.gov.br devolve 404 "Resource not found" quando não há dados
                return None
            if r.status_code == 429 or r.status_code >= 500:
                raise APIError(f"HTTP {r.status_code}: {r.text[:200]}")
            if r.status_code >= 400:
                # erro de parâmetro: não adianta repetir
                raise APIError(f"HTTP {r.status_code}: {r.text[:300]}")
            if not r.content.strip():
                raise APIError("resposta vazia")
            return r.json()
        except APIError as e:
            last_err = e
            if "HTTP 4" in str(e) and "HTTP 429" not in str(e):
                raise
        except (requests.RequestException, ValueError) as e:
            last_err = e
        if attempt < retries - 1:
            time.sleep(backoff * (2 ** attempt))
    raise APIError(f"Falha ao consultar {url}: {last_err}")


def get_bytes(url: str, *, timeout: int = 120, retries: int = 3) -> tuple[bytes, str]:
    """Baixa um arquivo (edital/TR). Retorna (conteúdo, content-type)."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = _session.get(url, timeout=timeout, headers={"Accept": "*/*"})
            r.raise_for_status()
            return r.content, r.headers.get("Content-Type", "")
        except requests.RequestException as e:
            last_err = e
            time.sleep(2 * (2 ** attempt))
    raise APIError(f"Falha ao baixar {url}: {last_err}")
