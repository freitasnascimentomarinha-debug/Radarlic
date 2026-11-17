"""Alerta diário de novos editais (roda no GitHub Actions; ver .github/workflows/alertas.yml).

Lê o perfil em alertas/perfil.json (mesmo formato do bloco "perfil" exportado pela tela
Meu perfil), busca no PNCP os editais publicados nas últimas N horas, pontua e envia os que
passam do score mínimo por Telegram e/ou e-mail.

Variáveis de ambiente (GitHub → Settings → Secrets and variables → Actions):
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID           (opcional)
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_TO   (opcional)
  SCORE_MIN (padrão 60), JANELA_HORAS (padrão 26)
"""
from __future__ import annotations

import html
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from core import pncp, scoring  # noqa: E402
from core.http import APIError  # noqa: E402


def carregar_perfil() -> dict:
    arq = RAIZ / "alertas" / "perfil.json"
    dados = json.loads(arq.read_text("utf-8"))
    return dados.get("perfil", dados)


def buscar(perfil: dict, horas: int) -> pd.DataFrame:
    frames = []
    for termo in perfil.get("palavras") or [""]:
        try:
            df, _ = pncp.buscar_editais(q=termo, status="recebendo_proposta", ufs=tuple(perfil.get("ufs") or ()),
                                        modalidades=(6, 8, 4), paginas=1, falhas=[])
            frames.append(df)
        except APIError as e:
            print(f"[aviso] busca '{termo}' falhou: {e}")
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames).drop_duplicates("pncp_id")
    if df.empty:
        return df
    corte = pd.Timestamp.now() - pd.Timedelta(hours=horas)
    df = df[df.publicacao >= corte]
    return scoring.pontuar(df, perfil)


def mensagem(df: pd.DataFrame) -> tuple[str, str]:
    linhas_txt, linhas_html = [], []
    for _, r in df.iterrows():
        fim = r.fim_propostas.strftime("%d/%m %H:%M") if pd.notna(r.fim_propostas) else "—"
        valor = f"R$ {r.valor_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") \
            if pd.notna(r.valor_estimado) else "—"
        linhas_txt.append(f"⭐ {r.score} | {r.modalidade} | {r.uf}\n{str(r.objeto)[:220]}\n"
                          f"{r.orgao}\nPropostas até {fim} · {valor}\n{r.link_pncp}\n")
        linhas_html.append(f"<b>⭐ {r.score}</b> · {html.escape(str(r.modalidade))} · {r.uf}\n"
                           f"{html.escape(str(r.objeto)[:220])}\n<i>{html.escape(str(r.orgao))}</i>\n"
                           f"Propostas até {fim} · {valor}\n<a href=\"{r.link_pncp}\">abrir no PNCP</a>\n")
    return "\n".join(linhas_txt), "\n".join(linhas_html)


def enviar_telegram(texto_html: str, n: int):
    tok, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return
    cab = f"📡 <b>RadarLic</b> — {n} novo(s) edital(is) para você\n\n"
    for i in range(0, len(texto_html), 3500):  # limite de 4096 caracteres por mensagem
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", timeout=30, data={
            "chat_id": chat, "text": (cab if i == 0 else "") + texto_html[i:i + 3500],
            "parse_mode": "HTML", "disable_web_page_preview": "true"}).raise_for_status()
    print("Telegram enviado.")


def enviar_email(texto: str, n: int):
    host, para = os.getenv("SMTP_HOST"), os.getenv("EMAIL_TO")
    if not (host and para):
        return
    msg = MIMEText(texto, "plain", "utf-8")
    msg["Subject"] = f"RadarLic: {n} novo(s) edital(is)"
    msg["From"] = os.getenv("SMTP_USER", "")
    msg["To"] = para
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=60) as s:
        s.starttls()
        s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
        s.sendmail(msg["From"], para.split(","), msg.as_string())
    print("E-mail enviado.")


def main():
    perfil = carregar_perfil()
    score_min = int(os.getenv("SCORE_MIN", "60"))
    df = buscar(perfil, int(os.getenv("JANELA_HORAS", "26")))
    df = df[df.score >= score_min] if not df.empty else df
    print(f"{len(df)} edital(is) com score >= {score_min}.")
    if df.empty:
        return
    txt, htm = mensagem(df.head(25))
    print(txt)
    enviar_telegram(htm, len(df))
    enviar_email(txt, len(df))


if __name__ == "__main__":
    main()
