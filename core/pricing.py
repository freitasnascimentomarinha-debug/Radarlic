"""Formação de preço para licitação (markup divisor).

preço = custo_direto / (1 - (impostos% + despesas_variaveis% + margem%))

Custos diretos: produto + frete + embalagem + outros por unidade.
Despesas variáveis sobre o preço: impostos, comissão, custo financeiro do prazo de
pagamento (definido no edital/contrato; em regra até 30 dias após o atesto da nota),
taxa da plataforma, custo da garantia contratual (arts. 96 a 98 da Lei 14.133/2021).
"""
from __future__ import annotations

from dataclasses import dataclass

# Alíquotas de referência (simplificadas). O usuário pode sobrescrever na tela.
REGIMES = {
    "Simples Nacional (comércio)": {"impostos": 8.0,
        "nota": "Use a alíquota EFETIVA do seu anexo/faixa (Anexo I: 4% a ~19%)."},
    "Lucro Presumido (comércio)": {"impostos": 3.65 + 2.28 + 0.0,
        "nota": "PIS 0,65% + COFINS 3% + IRPJ/CSLL presumidos ≈ 2,28%. Some o ICMS da operação (DIFAL em venda interestadual a órgão não contribuinte)."},
    "Lucro Real": {"impostos": 9.25 + 3.0,
        "nota": "PIS/COFINS não cumulativos 9,25% (com créditos) + IR/CSLL estimado. Ajuste com sua contabilidade."},
    "Personalizado": {"impostos": 0.0, "nota": "Informe o percentual total de tributos sobre o preço."},
}


@dataclass
class Entrada:
    custo_produto: float
    frete: float = 0.0
    outros_custos: float = 0.0
    impostos_pct: float = 8.0
    icms_pct: float = 0.0
    comissao_pct: float = 0.0
    plataforma_pct: float = 0.0
    prazo_pagamento_dias: int = 30
    juros_mes_pct: float = 1.5
    garantia_pct: float = 0.0
    margem_pct: float = 15.0
    quantidade: float = 1.0

    @property
    def custo_direto(self) -> float:
        return self.custo_produto + self.frete + self.outros_custos

    @property
    def financeiro_pct(self) -> float:
        return self.juros_mes_pct * self.prazo_pagamento_dias / 30

    @property
    def despesas_pct(self) -> float:
        # garantia contratual (até 5%, art. 98) tem custo de seguro-garantia ~ 1–2% do valor garantido
        return (self.impostos_pct + self.icms_pct + self.comissao_pct + self.plataforma_pct
                + self.financeiro_pct + self.garantia_pct)


def preco_venda(e: Entrada, margem_pct: float | None = None) -> float | None:
    m = e.margem_pct if margem_pct is None else margem_pct
    divisor = 1 - (e.despesas_pct + m) / 100
    if divisor <= 0:
        return None
    return e.custo_direto / divisor


def margem_no_preco(e: Entrada, preco: float) -> float:
    """Margem líquida (% do preço) obtida vendendo a `preco`."""
    if preco <= 0:
        return float("nan")
    lucro = preco * (1 - e.despesas_pct / 100) - e.custo_direto
    return 100 * lucro / preco


def decompor(e: Entrada, preco: float) -> dict:
    return {
        "Produto": e.custo_produto,
        "Frete": e.frete,
        "Outros custos": e.outros_custos,
        "Tributos": preco * (e.impostos_pct + e.icms_pct) / 100,
        "Comissão/plataforma": preco * (e.comissao_pct + e.plataforma_pct) / 100,
        "Custo financeiro": preco * e.financeiro_pct / 100,
        "Garantia": preco * e.garantia_pct / 100,
        "Lucro": preco - e.custo_direto - preco * e.despesas_pct / 100,
    }


def limite_inexequivel(valor_orcado: float) -> float:
    """Art. 59, §4º, Lei 14.133: em obras/serviços de engenharia, proposta < 75% do orçado é
    presumidamente inexequível. Para bens/serviços comuns, a jurisprudência do TCU usa
    o mesmo parâmetro como indício, que admite demonstração de exequibilidade."""
    return 0.75 * valor_orcado
