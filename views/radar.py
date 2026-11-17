import pandas as pd
import streamlit as st

from core import pncp, scoring, storage, theme
from core.http import APIError
from core.ui import brl, tabela_editais, aviso_api

cart = storage.carregar()
perfil = cart["perfil"]

theme.hero("🎯", "Radar de editais",
           "Pregões, dispensas e concorrências <b>abertos</b> ou <b>a abrir</b> no PNCP, ranqueados pelo seu perfil. "
           "Clique numa linha para analisar, salvar no funil ou abrir no sistema de disputa.")

with st.form("filtros"):
    c1, c2 = st.columns([2, 1])
    termo = c1.text_input("Palavra-chave do objeto",
                          placeholder="vazio = usa as palavras do seu perfil: " + ", ".join(perfil["palavras"][:5]))
    status = c2.selectbox("Situação", ["recebendo_proposta", "todos", "encerradas"],
                          format_func=pncp.STATUS.get)
    c3, c4, c5 = st.columns([2, 2, 1])
    ufs = c3.multiselect("UFs", pncp.UFS, default=perfil.get("ufs") or [])
    mods = c4.multiselect("Modalidades", list(pncp.MODALIDADES), default=[6, 8],
                          format_func=pncp.MODALIDADES.get)
    paginas = c5.number_input("Páginas (×100)", 1, 5, 1)
    buscar = st.form_submit_button("🔎 Buscar", type="primary", use_container_width=True)

termos = [termo] if termo.strip() else [p for p in perfil["palavras"] if p.strip()] or [""]
combos = len(termos) * max(1, len(ufs)) * max(1, len(mods))
if combos > 15:
    st.caption(f"⚠️ {combos} consultas ao PNCP (palavras × UFs × modalidades). Pode levar alguns minutos.")

if buscar or "radar_df" not in st.session_state:
    frames, total, falhas = [], 0, []
    prog = st.progress(0.0, "Consultando PNCP…")
    try:
        for i, t in enumerate(termos):
            try:
                df, n = pncp.buscar_editais(q=t, status=status, ufs=tuple(ufs), modalidades=tuple(mods),
                                            paginas=int(paginas), falhas=falhas)
                frames.append(df); total += n
            except APIError as e:
                falhas.append((t, None, None, str(e)))
            prog.progress((i + 1) / len(termos), f"Consultando PNCP… ({t or 'todos'})")
        df = pd.concat(frames) if frames else pd.DataFrame()
        if not df.empty:
            df = df.drop_duplicates("pncp_id")
        st.session_state.radar_df = scoring.pontuar(df, perfil)
        st.session_state.radar_total = total
        if falhas:
            st.warning(f"{len(falhas)} consulta(s) ao PNCP falharam e ficaram de fora: "
                       + "; ".join(f"'{f[0] or 'todos'}' {f[1] or ''} {f[2] or ''}".strip() for f in falhas[:6])
                       + ". Clique em Buscar de novo para tentar completar (o que já veio fica em cache).", icon="📡")
    except APIError as e:
        aviso_api(e)
        st.session_state.setdefault("radar_df", pd.DataFrame())
    prog.empty()

df = st.session_state.get("radar_df", pd.DataFrame())
if df.empty:
    st.info("Nenhum resultado. Ajuste os filtros ou as palavras do seu perfil (menu **Meu perfil**).")
    st.stop()

theme.kpis([
    {"rotulo": "Editais", "valor": len(df), "formato": "int", "icone": "📑", "cor": theme.INDIGO,
     "sub": f"de {st.session_state.get('radar_total', 0):,} no PNCP".replace(",", ".")},
    {"rotulo": "Score ≥ 70", "valor": int((df.score >= 70).sum()), "formato": "int", "icone": "⭐", "cor": theme.VERDE,
     "sub": "melhores oportunidades"},
    {"rotulo": "Encerram em 48h", "valor": int(((df.dias_para_fim >= 0) & (df.dias_para_fim <= 2)).sum()),
     "formato": "int", "icone": "⏱", "cor": theme.ROSA, "sub": "decida hoje"},
    {"rotulo": "A abrir", "valor": int((df.fase == "A abrir").sum()), "formato": "int", "icone": "🗓", "cor": theme.VIOLETA,
     "sub": "propostas ainda não abertas"},
    {"rotulo": "Valor estimado", "valor": df.valor_estimado.sum(), "formato": "brl", "icone": "💰", "cor": theme.CIANO,
     "sub": f"{int((df.modalidade_id == 8).sum())} dispensas"},
])

abas = st.tabs(["⭐ Melhores oportunidades", "🔨 Pregões", "⚡ Dispensas", "🗓️ A abrir", "📊 Visão geral"])
sel = None
with abas[0]:
    corte = st.select_slider("Score mínimo", list(range(0, 101, 5)), 50)
    sel = tabela_editais(df[df.score >= corte], "t_top") if sel is None else sel
with abas[1]:
    s = tabela_editais(df[df.modalidade_id.isin([6, 7])], "t_preg"); sel = sel if s is None else s
with abas[2]:
    st.caption("Dispensa eletrônica (art. 75 da Lei 14.133): disputa rápida, em geral 3 dias úteis de propostas.")
    s = tabela_editais(df[df.modalidade_id == 8], "t_disp"); sel = sel if s is None else s
with abas[3]:
    s = tabela_editais(df[df.fase == "A abrir"], "t_abrir"); sel = sel if s is None else s
with abas[4]:
    import plotly.express as px
    c1, c2 = st.columns(2)
    por_uf = df.groupby("uf").agg(editais=("pncp_id", "count"), valor=("valor_estimado", "sum")).reset_index()
    c1.plotly_chart(px.bar(por_uf.sort_values("editais", ascending=False), x="uf", y="editais",
                           title="Editais por UF", labels={"uf": "", "editais": "editais"}), use_container_width=True)
    venc = df.dropna(subset=["fim_propostas"]).copy()
    venc["dia"] = venc.fim_propostas.dt.date
    c2.plotly_chart(px.histogram(venc, x="dia", color="modalidade", title="Encerramento das propostas"),
                    use_container_width=True)
    st.plotly_chart(px.histogram(df, x="score", nbins=20, title="Distribuição do score"), use_container_width=True)

st.divider()
if sel is not None:
    with st.container(border=True):
        st.markdown(f"#### {sel['titulo'] or sel['pncp_id']}  " + theme.badge(f"score {sel.get('score', '—')}", theme.INDIGO)
                    + " " + theme.badge(sel["fase"], theme.VERDE), unsafe_allow_html=True)
        st.write(sel["objeto"])
        st.caption(f"{sel['orgao']} — {sel['municipio']}/{sel['uf']} · {sel['modalidade']} · "
                   f"{brl(sel['valor_estimado'])} · {sel.get('motivos', '')}")
        b1, b2, b3 = st.columns(3)
        if b1.button("📄 Abrir edital e analisar", type="primary", use_container_width=True):
            st.session_state.edital_sel = sel["pncp_id"]
            st.session_state.edital_meta = sel.to_dict()
            st.switch_page("views/edital.py")
        if b2.button("⭐ Salvar no funil", use_container_width=True):
            storage.salvar_edital(sel["pncp_id"], sel.to_dict()); st.toast("Edital salvo no funil (Triagem).", icon="⭐")
        b3.link_button("Ver no sistema de origem ↗", sel["link_origem"] or sel["link_pncp"], use_container_width=True)
else:
    st.caption("👆 Clique em uma linha para ver ações (analisar com IA, salvar, comparar).")

st.download_button("⬇️ Exportar resultado (CSV)", df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                   "radar_editais.csv", "text/csv")
