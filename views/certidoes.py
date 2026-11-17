import pandas as pd
import streamlit as st

from core import storage, theme
from core.grid import grid

cart = storage.carregar()
theme.hero("🛡️", "Certidões e habilitação",
           "Controle de validade dos documentos de habilitação (arts. 62 a 69 da Lei 14.133/2021). "
           "Certidão vencida no dia da sessão = inabilitação. Edite a coluna <b>Validade</b> (amarela) e salve.")

df = pd.DataFrame(cart.get("certidoes") or storage.CERTIDOES_PADRAO)
df["validade"] = pd.to_datetime(df["validade"], errors="coerce")
df["dias"] = (df["validade"] - pd.Timestamp.today().normalize()).dt.days

venc = int((df.dias < 0).sum()); breve = int(((df.dias >= 0) & (df.dias <= 15)).sum())
sem = int(df.validade.isna().sum()); ok = len(df) - venc - breve - sem
theme.kpis([
    {"rotulo": "Em dia", "valor": ok, "formato": "int", "icone": "✅", "cor": theme.VERDE},
    {"rotulo": "Vencem em 15 dias", "valor": breve, "formato": "int", "icone": "⏳", "cor": theme.AMBAR},
    {"rotulo": "Vencidas", "valor": venc, "formato": "int", "icone": "⛔", "cor": theme.ROSA},
    {"rotulo": "Sem data", "valor": sem, "formato": "int", "icone": "❔", "cor": theme.CINZA},
])

df = df.sort_values("dias", na_position="first").reset_index(drop=True)
_, ed = grid(df, "certs", {
    "documento": {"titulo": "Documento", "tipo": "longo", "min": 320, "editavel": True},
    "orgao": {"titulo": "Emissor", "largura": 180, "editavel": True},
    "validade": {"tipo": "data", "titulo": "Validade", "editavel": True, "largura": 140},
    "dias": {"tipo": "dias", "titulo": "Situação", "largura": 150},
    "link": {"tipo": "link", "titulo": "Emitir"},
}, editavel=True, selecao=False, busca=False)

c1, c2, c3 = st.columns(3)
if c1.button("💾 Salvar", type="primary", use_container_width=True):
    cart["certidoes"] = [
        {"documento": r["documento"], "orgao": r["orgao"], "link": r.get("link", "") or "",
         "validade": (str(r["validade"])[:10] if r["validade"] not in (None, "", "NaT") and pd.notna(r["validade"]) else None)}
        for _, r in df.assign(**{c: ed[c] for c in ("documento", "orgao", "validade")}).iterrows()]
    storage.salvar(); st.toast("Certidões salvas.", icon="✅"); st.rerun()
with c2.popover("➕ Adicionar documento", use_container_width=True):
    nd = st.text_input("Documento"); no = st.text_input("Emissor"); nl = st.text_input("Link para emissão")
    nv = st.date_input("Validade", value=None, format="DD/MM/YYYY")
    if st.button("Adicionar") and nd:
        cart["certidoes"].append({"documento": nd, "orgao": no, "link": nl, "validade": nv.isoformat() if nv else None})
        storage.salvar(); st.rerun()
if c3.button("↺ Restaurar lista padrão", use_container_width=True):
    cart["certidoes"] = storage.CERTIDOES_PADRAO; storage.salvar(); st.rerun()

with st.expander("📌 Dicas de habilitação"):
    st.markdown("""
- **SICAF em dia** substitui vários documentos nos pregões federais (art. 70, II, e art. 87 da Lei 14.133/2021).
- **ME/EPP**: a regularidade fiscal pode ser apresentada com restrição e regularizada em 5 dias úteis após declarado vencedor (art. 43, §1º, LC 123/2006).
- **Atestados de capacidade técnica**: guarde atestados de todo fornecimento a órgão público — o edital pode exigir até 50% do quantitativo licitado (art. 67, §2º).
- **Balanço**: exigido para qualificação econômico-financeira (art. 69); confira índices (LG, SG, LC ≥ 1) e o patrimônio líquido mínimo do edital.
- Antes de cada sessão, confira se a empresa não aparece no **CEIS/CNEP** e se as certidões valem até a data da disputa.
""")
