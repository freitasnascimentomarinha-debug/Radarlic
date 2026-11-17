"""RadarLic — inteligência para vender ao governo.

Execute:  streamlit run app.py
"""
import hmac

import streamlit as st

st.set_page_config(page_title="RadarLic", page_icon="📡", layout="wide")


def _senha_ok() -> bool:
    """Senha opcional (APP_PASSWORD em secrets) para o app publicado."""
    try:
        senha = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        senha = ""
    if not senha or st.session_state.get("autenticado"):
        return True
    st.title("📡 RadarLic")
    tentativa = st.text_input("Senha", type="password")
    if tentativa and hmac.compare_digest(tentativa, senha):
        st.session_state.autenticado = True
        st.rerun()
    elif tentativa:
        st.error("Senha incorreta.")
    return False


if not _senha_ok():
    st.stop()

from core import storage, theme  # noqa: E402

theme.aplicar()
storage.carregar()

paginas = {
    "": [
        st.Page("views/painel.py", title="Painel", icon="🏠", default=True),
    ],
    "Oportunidades": [
        st.Page("views/radar.py", title="Radar de editais", icon="🎯"),
        st.Page("views/edital.py", title="Edital + análise IA", icon="📄"),
        st.Page("views/comparador.py", title="Comparar editais", icon="⚖️"),
        st.Page("views/planejamento.py", title="Compras futuras (PCA)", icon="🗓️"),
        st.Page("views/atas.py", title="Atas e carona (ARP)", icon="🤝"),
    ],
    "Gestão": [
        st.Page("views/funil.py", title="Funil de propostas", icon="📊"),
        st.Page("views/agenda.py", title="Agenda de disputas", icon="📅"),
        st.Page("views/certidoes.py", title="Certidões e habilitação", icon="🛡️"),
        st.Page("views/documentos.py", title="Proposta e petições", icon="📝"),
    ],
    "Mercado": [
        st.Page("views/precos.py", title="Preços históricos", icon="💰"),
        st.Page("views/concorrentes.py", title="Concorrentes", icon="🏆"),
        st.Page("views/calculadora.py", title="Calculadora e chance de vencer", icon="🧮"),
    ],
    "Empresa": [
        st.Page("views/carteira.py", title="Meu perfil e carteira", icon="🏢"),
    ],
}
nav = st.navigation(paginas, expanded=True)

st.logo("assets/logo.svg", size="large")
with st.sidebar:
    st.caption("Fontes: PNCP · Compras.gov.br · BrasilAPI · IA: Claude")

nav.run()
