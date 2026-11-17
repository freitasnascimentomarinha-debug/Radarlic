import pandas as pd
import streamlit as st

from core import storage
from core.ui import brl

cart = storage.carregar()
st.title("⚖️ Comparar editais")

analises = cart["analises"]
salvos = cart["salvos"]
if not salvos and not analises:
    st.info("Salve editais no **Radar** ou analise-os com IA para compará-los aqui.")
    st.stop()

opcoes = list(dict.fromkeys(list(analises) + list(salvos)))


def rotulo(pid):
    s = salvos.get(pid, {})
    a = analises.get(pid, {})
    txt = a.get("resumo_objeto") or s.get("objeto") or ""
    return f"{'🤖 ' if pid in analises else ''}{pid} — {txt[:60]}"


sel = st.multiselect("Escolha de 2 a 4 editais (🤖 = já analisado por IA)", opcoes,
                     default=opcoes[:min(3, len(opcoes))], format_func=rotulo, max_selections=4)
if len(sel) < 2:
    st.stop()

CAMPOS = [
    ("Objeto", "resumo_objeto"), ("Órgão", "orgao"), ("Modalidade/critério", "modalidade_e_criterio"),
    ("Sessão pública", "data_sessao_publica"), ("Valor estimado", "valor_estimado"),
    ("Prazo de entrega", "prazo_entrega"), ("Local de entrega", "local_entrega"),
    ("Pagamento", "condicoes_pagamento"), ("Vigência", "vigencia"),
    ("Garantia contratual", "garantia_contratual"), ("Garantia do produto", "garantia_produto_assistencia"),
    ("Amostra", "amostra_ou_prova_conceito"), ("ME/EPP", "beneficio_me_epp"),
]
LISTAS = [("Qualificação técnica", "qualificacao_tecnica"),
          ("Econômico-financeira", "qualificacao_economico_financeira"),
          ("Pontos de atenção", "pontos_de_atencao"),
          ("Cláusulas restritivas", "clausulas_possivelmente_restritivas")]

tab = {}
for pid in sel:
    a, s = analises.get(pid, {}), salvos.get(pid, {})
    col = {"Viabilidade (IA)": f"{a['nota_viabilidade']}/10" if a else "não analisado",
           "Score do radar": s.get("score", "—"),
           "UF": s.get("uf", "—"),
           "Propostas até": str(s.get("fim_propostas", "—"))[:16]}
    for r, k in CAMPOS:
        col[r] = a.get(k) or (brl(float(s["valor_estimado"])) if k == "valor_estimado" and s.get("valor_estimado") not in (None, "", "nan") else s.get("objeto", "—") if k == "resumo_objeto" else "—")
    for r, k in LISTAS:
        col[r] = "\n".join(f"• {x}" for x in a.get(k, [])) or "—"
    col["Nº de exigências de habilitação"] = sum(len(a.get(k, [])) for k in
        ["habilitacao_juridica", "regularidade_fiscal_trabalhista", "qualificacao_tecnica",
         "qualificacao_economico_financeira"]) if a else "—"
    tab[pid] = col

df = pd.DataFrame(tab)
st.dataframe(df, use_container_width=True, height=900,
             column_config={c: st.column_config.TextColumn(c, width="large") for c in df.columns})
st.download_button("⬇️ Exportar comparação (CSV)", df.to_csv(sep=";").encode("utf-8-sig"), "comparacao.csv")

sem = [p for p in sel if p not in analises]
if sem:
    st.caption(f"{len(sem)} edital(is) sem análise de IA. Abra-os em **Edital + análise IA** para comparar exigências.")
