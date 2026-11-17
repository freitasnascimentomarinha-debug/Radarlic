from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import storage, theme
from core.theme import badge
from core.ui import brl

cart = storage.carregar()
perfil = cart["perfil"]
nome = perfil.get("empresa") or "sua empresa"
theme.hero("🏠", f"Bom dia, {nome}" if datetime.now().hour < 12 else f"Olá, {nome}",
           "Resumo do que precisa da sua atenção hoje: disputas próximas, propostas em andamento e documentos.")

salvos = pd.DataFrame(cart["salvos"].values()) if cart["salvos"] else pd.DataFrame()
agora = pd.Timestamp.now()
if not salvos.empty:
    salvos["fim"] = pd.to_datetime(salvos.get("fim_propostas"), errors="coerce")
    salvos["status"] = salvos.get("status", "Triagem").fillna("Triagem")
    salvos["valor"] = pd.to_numeric(salvos.get("valor_proposta"), errors="coerce").fillna(
        pd.to_numeric(salvos.get("valor_estimado"), errors="coerce"))

cert = pd.DataFrame(cart.get("certidoes", []))
cert["validade"] = pd.to_datetime(cert.get("validade"), errors="coerce")
cert["dias"] = (cert["validade"] - agora.normalize()).dt.days
cert_alerta = cert[(cert.validade.isna()) | (cert.dias <= 15)]

proximas = salvos[(salvos.fim >= agora) & (salvos.fim <= agora + pd.Timedelta(days=7))] if not salvos.empty else salvos
ativos = salvos[salvos.status.isin(["Cotando", "Proposta enviada", "Em disputa"])] if not salvos.empty else salvos
fechados = salvos[salvos.status.isin(["Ganho", "Perdido"])] if not salvos.empty else salvos
taxa = 100 * (fechados.status == "Ganho").mean() if len(fechados) else None
ganho = salvos.loc[salvos.status == "Ganho", "valor"].sum() if not salvos.empty else 0

theme.kpis([
    {"rotulo": "Disputas em 7 dias", "valor": len(proximas), "formato": "int", "icone": "⏱", "cor": theme.ROSA,
     "sub": "editais salvos encerrando"},
    {"rotulo": "Em andamento", "valor": len(ativos), "formato": "int", "icone": "📤", "cor": theme.INDIGO,
     "sub": brl(ativos["valor"].sum(), 0) + " em jogo" if len(ativos) else "nenhuma proposta ativa"},
    {"rotulo": "Taxa de vitória", "valor": taxa, "formato": "pct", "icone": "🏆", "cor": theme.VERDE,
     "sub": f"{len(fechados)} disputas concluídas"},
    {"rotulo": "Valor ganho", "valor": ganho, "formato": "brl", "icone": "💰", "cor": theme.CIANO,
     "sub": "status Ganho no funil"},
    {"rotulo": "Certidões a renovar", "valor": len(cert_alerta), "formato": "int", "icone": "🛡", "cor": theme.AMBAR,
     "sub": "vencidas, sem data ou ≤ 15 dias"},
])

c1, c2 = st.columns([1.3, 1])
with c1:
    with st.container(border=True):
        st.markdown("#### ⏱ Próximas disputas")
        futuras = salvos[salvos.fim >= agora].sort_values("fim").head(8) if not salvos.empty else salvos
        if futuras.empty:
            st.caption("Nenhuma disputa futura na carteira. Salve editais pelo **Radar**.")
        for _, r in futuras.iterrows():
            h = (r.fim - agora).total_seconds() / 3600
            cor = theme.ROSA if h < 24 else theme.AMBAR if h < 72 else theme.VERDE
            falta = f"{int(h)}h" if h < 48 else f"{int(h // 24)} dias"
            st.markdown(
                f"<div class='rl-tl'><div style='display:flex;justify-content:space-between;gap:8px'>"
                f"<b>{(r.get('objeto') or '')[:110]}</b>{badge('em ' + falta, cor)}</div>"
                f"<div style='color:#64748b;font-size:.85rem'>{r.get('orgao') or ''} · {r.get('uf') or ''} · "
                f"{r.fim.strftime('%d/%m %H:%M')} · {badge(r.status, storage.CORES_FUNIL.get(r.status, '#64748b'))}</div></div>",
                unsafe_allow_html=True)
        if st.button("Abrir agenda completa →"):
            st.switch_page("views/agenda.py")
with c2:
    with st.container(border=True):
        st.markdown("#### 📊 Funil")
        if salvos.empty:
            st.caption("Sem editais na carteira.")
        else:
            cont = salvos.status.value_counts().reindex(storage.STATUS_FUNIL[:5]).fillna(0)
            fig = go.Figure(go.Funnel(y=cont.index, x=cont.values, textinfo="value",
                                      marker=dict(color=[storage.CORES_FUNIL[s] for s in cont.index])))
            fig.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
    with st.container(border=True):
        st.markdown("#### 🛡 Documentos")
        if cert_alerta.empty:
            st.success("Todas as certidões estão em dia.")
        for _, r in cert_alerta.head(5).iterrows():
            st_txt = "sem data" if pd.isna(r.dias) else (f"vencida há {-int(r.dias)}d" if r.dias < 0 else f"vence em {int(r.dias)}d")
            cor = theme.ROSA if pd.isna(r.dias) or r.dias < 0 else theme.AMBAR
            st.markdown(f"<div class='rl-card'><div class='t'>{r.documento}</div>{badge(st_txt, cor)}</div>",
                        unsafe_allow_html=True)
        if st.button("Gerenciar certidões →"):
            st.switch_page("views/certidoes.py")

st.markdown("#### Atalhos")
a = st.columns(4)
for col, (txt, pg) in zip(a, [("🎯 Buscar editais", "views/radar.py"), ("💰 Pesquisar preço", "views/precos.py"),
                               ("📄 Analisar edital com IA", "views/edital.py"), ("🤝 Atas para carona", "views/atas.py")]):
    if col.button(txt, use_container_width=True):
        st.switch_page(pg)
