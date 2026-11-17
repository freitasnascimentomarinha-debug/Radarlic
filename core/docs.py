"""Geração de documentos: proposta comercial (.docx), petições (.docx) e agenda (.ics)."""
from __future__ import annotations

import io
from datetime import date, datetime, timedelta

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

from .ui import brl

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]


def _data_extenso(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _base() -> Document:
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = sec.bottom_margin = Cm(2)
    sec.left_margin = sec.right_margin = Cm(2.2)
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(11)
    return doc


def _sombrear(cell, cor="E0E7FF"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), cor)
    tcPr.append(shd)


def _cabecalho_empresa(doc: Document, perfil: dict):
    p = doc.add_paragraph()
    r = p.add_run(perfil.get("empresa") or "RAZÃO SOCIAL DA EMPRESA")
    r.bold = True; r.font.size = Pt(14); r.font.color.rgb = RGBColor(0x31, 0x2E, 0x81)
    linhas = [f"CNPJ: {perfil.get('cnpj') or '__.___.___/____-__'}", perfil.get("endereco") or "",
              " · ".join(x for x in [perfil.get("telefone"), perfil.get("email")] if x)]
    for l in filter(None, linhas):
        q = doc.add_paragraph(l); q.paragraph_format.space_after = Pt(0)
        q.runs[0].font.size = Pt(9); q.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    doc.add_paragraph()


def proposta_docx(perfil: dict, edital: dict, itens: pd.DataFrame, validade_dias: int = 60,
                  prazo_entrega: str = "", local: str = "") -> bytes:
    """itens: colunas item, descricao, marca, modelo, unidade, quantidade, valor_unitario."""
    doc = _base()
    _cabecalho_empresa(doc, perfil)
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("PROPOSTA COMERCIAL"); r.bold = True; r.font.size = Pt(15)

    doc.add_paragraph(f"Ao(À) {edital.get('orgao') or 'Órgão contratante'}")
    doc.add_paragraph(f"Referência: {edital.get('titulo') or ''} — Processo/controle PNCP {edital.get('pncp_id', '')}")
    doc.add_paragraph(f"Objeto: {edital.get('objeto') or ''}")

    tab = doc.add_table(rows=1, cols=8)
    tab.style = "Table Grid"; tab.alignment = WD_TABLE_ALIGNMENT.CENTER
    cab = ["Item", "Descrição", "Marca", "Modelo", "Un.", "Qtd.", "Valor unit.", "Valor total"]
    for c, h in zip(tab.rows[0].cells, cab):
        c.text = h; c.paragraphs[0].runs[0].bold = True; _sombrear(c)
    total = 0.0
    for _, it in itens.iterrows():
        q = float(it.get("quantidade") or 0); v = float(it.get("valor_unitario") or 0); total += q * v
        vals = [str(it.get("item", "")), str(it.get("descricao", ""))[:400], str(it.get("marca", "") or ""),
                str(it.get("modelo", "") or ""), str(it.get("unidade", "") or ""),
                f"{q:,.0f}".replace(",", "."), brl(v), brl(q * v)]
        for c, val in zip(tab.add_row().cells, vals):
            c.text = val
            for pr in c.paragraphs:
                for rr in pr.runs:
                    rr.font.size = Pt(9)
    linha = tab.add_row().cells
    linha[0].merge(linha[6]).text = "VALOR GLOBAL DA PROPOSTA"
    linha[7].text = brl(total)
    for c in (linha[0], linha[7]):
        c.paragraphs[0].runs[0].bold = True; _sombrear(c, "EEF2FF")

    doc.add_paragraph()
    doc.add_paragraph(f"Valor global: {brl(total)}.")
    for txt in [
        f"Validade da proposta: {validade_dias} dias corridos a contar da data de sua apresentação.",
        f"Prazo de entrega: {prazo_entrega or 'conforme Termo de Referência'}.",
        f"Local de entrega: {local or 'conforme Termo de Referência'}.",
        "Nos preços ofertados estão incluídos todos os custos diretos e indiretos, tributos, encargos "
        "sociais, trabalhistas, previdenciários, fiscais e comerciais, frete, seguros e demais despesas "
        "necessárias ao fiel cumprimento do objeto.",
        "Declaramos que o objeto ofertado atende integralmente às especificações do edital e do Termo de Referência.",
        f"Dados bancários: {perfil.get('banco') or 'Banco ___ / Agência ___ / Conta ___'}.",
    ]:
        doc.add_paragraph(txt, style="List Bullet")

    doc.add_paragraph()
    doc.add_paragraph(f"{perfil.get('endereco', '').split(',')[-1].strip() or 'Cidade'}, {_data_extenso(date.today())}.")
    doc.add_paragraph("\n\n_____________________________________________")
    doc.add_paragraph(f"{perfil.get('responsavel') or 'Nome do representante legal'}\n{perfil.get('cargo') or ''}")
    buf = io.BytesIO(); doc.save(buf)
    return buf.getvalue()


def peticao_docx(perfil: dict, titulo: str, destinatario: str, corpo: str) -> bytes:
    doc = _base()
    _cabecalho_empresa(doc, perfil)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(titulo.upper()); r.bold = True; r.font.size = Pt(13)
    doc.add_paragraph(destinatario)
    for par in corpo.split("\n"):
        q = doc.add_paragraph(par)
        q.paragraph_format.first_line_indent = Cm(1.25) if par and not par[:2].strip().isdigit() else None
        q.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    doc.add_paragraph(f"\n{_data_extenso(date.today())}.\n\n_____________________________________________")
    doc.add_paragraph(f"{perfil.get('responsavel') or 'Representante legal'} – {perfil.get('empresa') or ''}")
    buf = io.BytesIO(); doc.save(buf)
    return buf.getvalue()


def ics(eventos: list[dict]) -> bytes:
    """eventos: {titulo, inicio(datetime), descricao, url}. Lembrete 1 dia antes."""
    def f(d: datetime) -> str:
        return d.strftime("%Y%m%dT%H%M%S")
    linhas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RadarLic//PT-BR", "CALSCALE:GREGORIAN"]
    for i, e in enumerate(eventos):
        ini = pd.Timestamp(e["inicio"]).to_pydatetime()
        desc = (e.get("descricao") or "").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")
        linhas += ["BEGIN:VEVENT", f"UID:radarlic-{i}-{f(ini)}@radarlic", f"DTSTAMP:{f(datetime.now())}",
                   f"DTSTART:{f(ini)}", f"DTEND:{f(ini + timedelta(hours=1))}",
                   f"SUMMARY:{e['titulo'][:120].replace(',', ' ')}", f"DESCRIPTION:{desc[:900]}",
                   f"URL:{e.get('url') or ''}",
                   "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", "DESCRIPTION:Lembrete RadarLic", "END:VALARM",
                   "END:VEVENT"]
    linhas.append("END:VCALENDAR")
    return "\r\n".join(linhas).encode("utf-8")
