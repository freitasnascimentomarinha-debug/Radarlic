"""Pontuação de oportunidades (0–100), transparente: cada critério mostra quanto somou."""
from __future__ import annotations

import pandas as pd

from .compras import _norm

PESOS = {"aderencia": 40, "prazo": 20, "valor": 15, "local": 15, "competicao": 10}

REGIOES = {
    "N": {"AC", "AM", "AP", "PA", "RO", "RR", "TO"},
    "NE": {"AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"},
    "CO": {"DF", "GO", "MS", "MT"},
    "SE": {"ES", "MG", "RJ", "SP"},
    "S": {"PR", "RS", "SC"},
}


def _regiao(uf):
    return next((r for r, s in REGIOES.items() if uf in s), None)


def pontuar(df: pd.DataFrame, perfil: dict) -> pd.DataFrame:
    if df.empty:
        return df
    palavras = [_norm(p).strip() for p in perfil.get("palavras", []) if p.strip()]
    ufs = set(perfil.get("ufs", []))
    sede = perfil.get("uf_sede")
    vmin, vmax = perfil.get("valor_min", 0) or 0, perfil.get("valor_max", 0) or 0
    me_epp = perfil.get("me_epp", False)

    notas, motivos = [], []
    for _, r in df.iterrows():
        texto = _norm(f"{r.get('objeto', '')} {r.get('titulo', '')}")
        m, pts = [], {}

        # 1) aderência ao portfólio
        if palavras:
            hits = [p for p in palavras if p and p in texto]
            pts["aderencia"] = 0 if not hits else min(1.0, 0.6 + 0.2 * (len(hits) - 1))
            if hits:
                m.append("palavras: " + ", ".join(hits[:4]))
        else:
            pts["aderencia"] = 0.5

        # 2) prazo — tempo suficiente para cotar com fornecedor e montar documentação
        d = r.get("dias_para_fim")
        if r.get("fase") == "A abrir":
            pts["prazo"] = 0.9; m.append("a abrir")
        elif pd.isna(d):
            pts["prazo"] = 0.5
        elif d < 1:
            pts["prazo"] = 0.1; m.append("encerra < 24h")
        elif d < 3:
            pts["prazo"] = 0.5; m.append(f"{d:.0f}d p/ encerrar")
        elif d <= 20:
            pts["prazo"] = 1.0; m.append(f"{d:.0f}d p/ encerrar")
        else:
            pts["prazo"] = 0.8

        # 3) valor dentro da faixa de capacidade
        v = r.get("valor_estimado")
        if pd.isna(v) or not v:
            pts["valor"] = 0.5
        elif (not vmin or v >= vmin) and (not vmax or v <= vmax):
            pts["valor"] = 1.0
        else:
            pts["valor"] = 0.2; m.append("valor fora da faixa")

        # 4) localização (frete e prazo de entrega)
        uf = r.get("uf")
        if uf == sede or uf in ufs:
            pts["local"] = 1.0; m.append(f"UF {uf}")
        elif sede and _regiao(uf) == _regiao(sede):
            pts["local"] = 0.6
        else:
            pts["local"] = 0.25

        # 5) competição esperada
        mod = r.get("modalidade_id")
        info = _norm(str(r.get("info") or "") + " " + texto)
        pts["competicao"] = {8: 1.0, 6: 0.6, 7: 0.7}.get(mod, 0.4)
        if mod == 8:
            m.append("dispensa (menos concorrência)")
        if me_epp and ("exclusiv" in info and ("me epp" in info or "microempresa" in info)):
            pts["competicao"] = min(1.0, pts["competicao"] + 0.4); m.append("exclusivo ME/EPP")

        notas.append(round(sum(PESOS[k] * pts[k] for k in PESOS)))
        motivos.append(" · ".join(m))
    out = df.copy()
    out["score"] = notas
    out["motivos"] = motivos
    return out.sort_values(["score", "fim_propostas"], ascending=[False, True])
