import pandas as pd
import streamlit as st

from core import pncp, storage, theme
from core.grid import grid

cart = storage.carregar()
p = cart["perfil"]

theme.hero("🏢", "Meu perfil e carteira",
           "Os dados da empresa entram na proposta e nas petições; as palavras-chave, UFs e faixa de valor alimentam o "
           "score do Radar.")

with st.form("perfil"):
    st.markdown("##### 🏢 Dados da empresa (usados nos documentos)")
    c1, c2 = st.columns([2, 1])
    p["empresa"] = c1.text_input("Razão social", p.get("empresa", ""))
    p["cnpj"] = c2.text_input("CNPJ", p.get("cnpj", ""))
    p["endereco"] = st.text_input("Endereço completo (termine com a cidade/UF)", p.get("endereco", ""))
    c1, c2, c3 = st.columns(3)
    p["telefone"] = c1.text_input("Telefone", p.get("telefone", ""))
    p["email"] = c2.text_input("E-mail comercial", p.get("email", ""))
    p["banco"] = c3.text_input("Dados bancários", p.get("banco", ""), placeholder="Banco 001 / Ag. 0000 / CC 00000-0")
    c1, c2 = st.columns(2)
    p["responsavel"] = c1.text_input("Representante legal", p.get("responsavel", ""))
    p["cargo"] = c2.text_input("Cargo", p.get("cargo", ""))
    st.markdown("##### 🎯 O que você vende e onde")
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
    df["analisado"] = df["pncp_id"].map(lambda x: "🤖 sim" if x in cart["analises"] else "—")
    grid(df, "salvos", {"status": {"tipo": "badge", "titulo": "Status", "cores": storage.CORES_FUNIL, "largura": 150},
                        "fim_propostas": {"tipo": "prazo", "titulo": "Propostas até"},
                        "objeto": {"tipo": "longo", "titulo": "Objeto"}, "orgao": {"titulo": "Órgão", "largura": 200},
                        "uf": {"titulo": "UF", "largura": 70}, "valor_estimado": {"tipo": "brl", "titulo": "Estimado"},
                        "analisado": {"titulo": "IA", "largura": 90}, "pncp_id": {"titulo": "PNCP", "largura": 230}},
         selecao=False)
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
