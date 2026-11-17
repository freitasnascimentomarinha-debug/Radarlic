import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from core import storage, theme
from core.grid import grid

cart = storage.carregar()
theme.hero("📊", "Funil de propostas",
           "Acompanhe cada edital da triagem ao resultado. Edite <b>status</b>, <b>valor da proposta</b>, "
           "<b>responsável</b> e <b>anotações</b> direto na tabela (células em amarelo) e clique em Salvar.")

if not cart["salvos"]:
    st.info("Nenhum edital no funil. No **Radar**, selecione um edital e clique em **Salvar no funil**.")
    st.stop()

df = pd.DataFrame(cart["salvos"].values())
for c, v in {"status": "Triagem", "valor_proposta": None, "responsavel": "", "obs": ""}.items():
    if c not in df:
        df[c] = v
df["status"] = df["status"].fillna("Triagem")
df["valor_estimado"] = pd.to_numeric(df.get("valor_estimado"), errors="coerce")
df["valor_proposta"] = pd.to_numeric(df["valor_proposta"], errors="coerce")
df["analise"] = df["pncp_id"].map(lambda p: "🤖 analisado" if p in cart["analises"] else "—")

fechados = df[df.status.isin(["Ganho", "Perdido"])]
ganhos = df[df.status == "Ganho"]
theme.kpis([
    {"rotulo": "No funil", "valor": len(df), "formato": "int", "icone": "🗂", "cor": theme.INDIGO},
    {"rotulo": "Propostas ativas", "valor": int(df.status.isin(["Cotando", "Proposta enviada", "Em disputa"]).sum()),
     "formato": "int", "icone": "📤", "cor": theme.CIANO},
    {"rotulo": "Taxa de vitória", "valor": 100 * len(ganhos) / len(fechados) if len(fechados) else None,
     "formato": "pct", "icone": "🏆", "cor": theme.VERDE, "sub": f"{len(ganhos)} ganhos / {len(fechados)} concluídos"},
    {"rotulo": "Valor ganho", "valor": ganhos.valor_proposta.fillna(ganhos.valor_estimado).sum(), "formato": "brl",
     "icone": "💰", "cor": theme.AMBAR},
])

filtro = st.segmented_control("Mostrar", ["Todos", "Ativos", "Concluídos"], default="Todos")
vis = df
if filtro == "Ativos":
    vis = df[~df.status.isin(["Ganho", "Perdido", "Desistência"])]
elif filtro == "Concluídos":
    vis = df[df.status.isin(["Ganho", "Perdido", "Desistência"])]

linha, editado = grid(vis, "funil", {
    "status": {"tipo": "select", "titulo": "Status", "opcoes": storage.STATUS_FUNIL,
               "cores": storage.CORES_FUNIL, "fixa": True, "largura": 160},
    "fim_propostas": {"tipo": "prazo", "titulo": "Propostas até"},
    "objeto": {"tipo": "longo", "titulo": "Objeto", "min": 300},
    "orgao": {"titulo": "Órgão", "largura": 200},
    "uf": {"titulo": "UF", "largura": 70},
    "valor_estimado": {"tipo": "brl", "titulo": "Estimado", "largura": 140},
    "valor_proposta": {"tipo": "brl", "titulo": "Minha proposta", "editavel": True, "largura": 150},
    "responsavel": {"titulo": "Responsável", "editavel": True, "largura": 140},
    "obs": {"tipo": "longo", "titulo": "Anotações", "editavel": True, "min": 220, "flex": 1},
    "analise": {"titulo": "IA", "largura": 110},
    "link_pncp": {"tipo": "link", "titulo": "PNCP"},
}, editavel=True)

c1, c2, c3 = st.columns([1, 1, 2])
if c1.button("💾 Salvar alterações", type="primary", use_container_width=True):
    base = vis.reset_index(drop=True)
    for rid, ed in editado.iterrows():
        s = cart["salvos"][base.iloc[rid]["pncp_id"]]
        s["status"] = ed["status"]
        s["valor_proposta"] = None if pd.isna(ed["valor_proposta"]) else float(ed["valor_proposta"])
        s["responsavel"] = ed["responsavel"] or ""
        s["obs"] = ed["obs"] or ""
    storage.salvar(); st.toast("Funil atualizado.", icon="✅"); st.rerun()
if linha is not None:
    if c2.button("📄 Abrir edital", use_container_width=True):
        st.session_state.edital_sel = linha["pncp_id"]; st.switch_page("views/edital.py")
    if c3.button("📝 Gerar proposta comercial deste edital", use_container_width=True):
        st.session_state.edital_sel = linha["pncp_id"]; st.switch_page("views/documentos.py")

g1, g2 = st.columns(2)
with g1:
    cont = df.status.value_counts().reindex(storage.STATUS_FUNIL).fillna(0)
    fig = go.Figure(go.Funnel(y=cont.index[:5], x=cont.values[:5], textinfo="value+percent initial",
                              marker=dict(color=[storage.CORES_FUNIL[s] for s in cont.index[:5]])))
    fig.update_layout(title="Conversão", height=340)
    st.plotly_chart(fig, use_container_width=True)
with g2:
    val = df.assign(v=df.valor_proposta.fillna(df.valor_estimado)).groupby("status").v.sum().reindex(storage.STATUS_FUNIL).dropna()
    st.plotly_chart(px.pie(values=val.values, names=val.index, hole=.55, title="Valor por status",
                           color=val.index, color_discrete_map=storage.CORES_FUNIL).update_layout(height=340),
                    use_container_width=True)
