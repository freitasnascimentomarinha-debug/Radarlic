import pandas as pd
import streamlit as st

from core import pncp, storage

cart = storage.carregar()
p = cart["perfil"]

st.title("🏢 Meu perfil e carteira")
st.caption("O perfil alimenta o score do Radar e os rankings de concorrentes.")

with st.form("perfil"):
    p["empresa"] = st.text_input("Nome da empresa", p.get("empresa", ""))
    palavras = st.text_area("Palavras-chave do que você vende (uma por linha)", "\n".join(p.get("palavras", [])),
                            help="Termos que aparecem no objeto dos editais: 'papel sulfite', 'toner', 'luva nitrílica'…")
    c1, c2 = st.columns(2)
    ufs = c1.multiselect("UFs onde atende", pncp.UFS, default=p.get("ufs", []))
    sede = c2.selectbox("UF da sede", pncp.UFS, index=pncp.UFS.index(p.get("uf_sede", "RJ")))
    c1, c2, c3 = st.columns(3)
    vmin = c1.number_input("Valor mínimo de interesse (R$)", 0.0, value=float(p.get("valor_min", 0)))
    vmax = c2.number_input("Valor máximo que consegue atender (R$)", 0.0, value=float(p.get("valor_max", 0)),
                           help="0 = sem limite")
    me = c3.toggle("Sou ME/EPP", value=p.get("me_epp", True),
                   help="LC 123/2006: itens até R$ 80 mil exclusivos e empate ficto de 5% no pregão.")
    catmats = st.text_input("Códigos CATMAT/CATSER do seu portfólio (vírgula)", ", ".join(p.get("catmats", [])))
    if st.form_submit_button("💾 Salvar perfil", type="primary"):
        p.update({"palavras": [x.strip() for x in palavras.splitlines() if x.strip()], "ufs": ufs,
                  "uf_sede": sede, "valor_min": vmin, "valor_max": vmax, "me_epp": me,
                  "catmats": [x.strip() for x in catmats.split(",") if x.strip()]})
        storage.salvar()
        st.session_state.pop("radar_df", None)
        st.success("Perfil salvo.")

st.subheader("⭐ Editais salvos")
if cart["salvos"]:
    df = pd.DataFrame(cart["salvos"].values())
    cols = [c for c in ["pncp_id", "objeto", "orgao", "uf", "fim_propostas", "valor_estimado", "score"] if c in df]
    df["analisado"] = df["pncp_id"].isin(cart["analises"])
    st.dataframe(df[cols + ["analisado"]], hide_index=True, use_container_width=True)
    rem = st.multiselect("Remover", list(cart["salvos"]))
    if rem and st.button("Remover selecionados"):
        for r in rem:
            cart["salvos"].pop(r, None); cart["analises"].pop(r, None)
        storage.salvar(); st.rerun()
else:
    st.caption("Nenhum edital salvo ainda.")

st.subheader("💾 Backup")
st.caption("No Streamlit Community Cloud os arquivos do servidor são apagados quando o app reinicia. "
           "Exporte a carteira periodicamente e importe quando precisar.")
c1, c2 = st.columns(2)
c1.download_button("⬇️ Exportar carteira (JSON)", storage.exportar(), "radarlic_carteira.json", "application/json")
arq = c2.file_uploader("Importar carteira", type="json")
if arq and st.button("Importar"):
    storage.importar(arq.getvalue()); st.success("Carteira importada."); st.rerun()
