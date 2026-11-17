"""Análise de edital com IA (Claude).

O PDF é enviado direto ao modelo (lê texto, tabelas e até páginas escaneadas).
A saída é JSON validado contra um schema fixo (structured outputs), o que permite
comparar editais lado a lado e montar checklist automaticamente.
"""
from __future__ import annotations

import base64
import io
import json
import zipfile

import streamlit as st

MODELO = "claude-opus-5-5"
LIMITE_PDF_BYTES = 25 * 1024 * 1024  # margem sob o teto de 32 MB por requisição

_lista = {"type": "array", "items": {"type": "string"}}
_txt = {"type": "string"}

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "resumo_objeto": _txt,
        "orgao": _txt,
        "modalidade_e_criterio": _txt,
        "data_sessao_publica": _txt,
        "prazo_propostas": _txt,
        "valor_estimado": _txt,
        "prazo_entrega": _txt,
        "local_entrega": _txt,
        "condicoes_pagamento": _txt,
        "vigencia": _txt,
        "garantia_contratual": _txt,
        "garantia_produto_assistencia": _txt,
        "amostra_ou_prova_conceito": _txt,
        "beneficio_me_epp": _txt,
        "permite_consorcio_subcontratacao": _txt,
        "habilitacao_juridica": _lista,
        "regularidade_fiscal_trabalhista": _lista,
        "qualificacao_tecnica": _lista,
        "qualificacao_economico_financeira": _lista,
        "documentos_proposta": _lista,
        "penalidades": _lista,
        "pontos_de_atencao": _lista,
        "clausulas_possivelmente_restritivas": _lista,
        "itens_principais": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"item": _txt, "descricao": _txt, "quantidade": _txt,
                               "unidade": _txt, "valor_unitario_estimado": _txt},
                "required": ["item", "descricao", "quantidade", "unidade", "valor_unitario_estimado"],
            },
        },
        "checklist": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"tarefa": _txt, "prazo": _txt},
                "required": ["tarefa", "prazo"],
            },
        },
        "nota_viabilidade": {"type": "integer"},
        "justificativa_nota": _txt,
    },
}
SCHEMA["required"] = list(SCHEMA["properties"].keys())

SISTEMA = """Você é analista sênior de licitações de uma empresa fornecedora que vende para a
administração pública brasileira. Domina a Lei 14.133/2021, a LC 123/2006 (benefícios ME/EPP),
o Decreto 11.462/2023 (SRP) e a IN SEGES 73/2022 (licitação eletrônica).

Tarefa: ler o edital/termo de referência anexado e extrair, para o empresário decidir se participa,
tudo o que ele precisa cumprir. Regras:
- Use somente o que está nos documentos. Quando a informação não existir, escreva
  "Não informado no documento". Não invente prazos, valores ou exigências.
- Sempre que possível, indique entre parênteses a cláusula/item de origem, ex.: "(item 9.3)".
- Em listas de habilitação, um documento por linha, com o detalhe exigido (ex.: atestado com
  quantitativo mínimo de 50%).
- Em "pontos_de_atencao": riscos práticos (prazo de entrega curto, entrega fracionada em vários
  endereços, multas altas, amostra obrigatória, exigência de marca, garantia longa, pagamento
  condicionado, vistoria obrigatória).
- Em "clausulas_possivelmente_restritivas": exigências que podem ferir a competitividade
  (art. 9º, I; art. 67; art. 41 da Lei 14.133), com o fundamento — servem de base para
  pedido de esclarecimento ou impugnação (prazo: até 3 dias úteis antes da abertura, art. 164).
- "checklist": ações concretas para a empresa, com prazo absoluto quando o edital permitir calcular.
- "nota_viabilidade" de 0 a 10 para uma empresa comercial de pequeno/médio porte participar,
  considerando complexidade de habilitação, riscos e prazos; justifique em 2–3 frases.
- Escreva em português do Brasil, objetivo."""


def _cliente():
    import anthropic
    try:
        chave = st.secrets.get("ANTHROPIC_API_KEY", None)
    except Exception:  # sem secrets.toml
        chave = None
    try:
        return anthropic.Anthropic(api_key=chave) if chave else anthropic.Anthropic()
    except Exception as e:  # sem credencial configurada
        raise RuntimeError("Configure ANTHROPIC_API_KEY em .streamlit/secrets.toml ou nas Secrets do Streamlit Cloud.") from e


def preparar_documentos(arquivos: list[tuple[str, bytes]]) -> list[dict]:
    """Converte (nome, bytes) em blocos de conteúdo. Abre .zip e extrai PDFs. PDFs muito
    grandes viram texto (pypdf) para caber no limite da requisição."""
    expandidos: list[tuple[str, bytes]] = []
    for nome, dados in arquivos:
        if dados[:2] == b"PK" and not nome.lower().endswith((".docx", ".xlsx")):
            try:
                with zipfile.ZipFile(io.BytesIO(dados)) as z:
                    for n in z.namelist():
                        if n.lower().endswith((".pdf", ".txt")):
                            expandidos.append((n, z.read(n)))
                continue
            except zipfile.BadZipFile:
                pass
        expandidos.append((nome, dados))

    blocos, total = [], 0
    for nome, dados in expandidos:
        if dados[:4] == b"%PDF":
            if total + len(dados) <= LIMITE_PDF_BYTES:
                total += len(dados)
                blocos.append({
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf",
                               "data": base64.standard_b64encode(dados).decode()},
                    "title": nome,
                })
            else:
                from pypdf import PdfReader
                texto = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(dados)).pages)
                blocos.append({"type": "document",
                               "source": {"type": "text", "media_type": "text/plain", "data": texto},
                               "title": nome})
        elif nome.lower().endswith(".docx"):
            texto = _docx_texto(dados)
            if texto:
                blocos.append({"type": "document",
                               "source": {"type": "text", "media_type": "text/plain", "data": texto},
                               "title": nome})
        else:
            try:
                texto = dados.decode("utf-8")
                blocos.append({"type": "document",
                               "source": {"type": "text", "media_type": "text/plain", "data": texto},
                               "title": nome})
            except UnicodeDecodeError:
                continue
    return blocos


def _docx_texto(dados: bytes) -> str:
    import re
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        return re.sub(r"<[^>]+>", "", xml)
    except Exception:
        return ""


def analisar(arquivos: list[tuple[str, bytes]], contexto: str = "", esforco: str = "medium") -> dict:
    """Envia os documentos ao Claude e devolve o dicionário no formato de SCHEMA."""
    import anthropic
    blocos = preparar_documentos(arquivos)
    if not blocos:
        raise RuntimeError("Nenhum documento legível (PDF, DOCX ou TXT) encontrado.")
    client = _cliente()
    conteudo = blocos + [{"type": "text", "text":
        "Analise os documentos acima conforme as instruções." +
        (f"\n\nContexto do PNCP: {contexto}" if contexto else "")}]
    try:
        with client.beta.messages.stream(
            model=MODELO,
            max_tokens=32000,
            system=SISTEMA,
            messages=[{"role": "user", "content": conteudo}],
            thinking={"type": "adaptive"},
            output_config={"effort": esforco,
                           "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.AuthenticationError as e:
        raise RuntimeError("Chave da API Anthropic inválida.") from e
    except anthropic.RateLimitError as e:
        raise RuntimeError("Limite de uso da API atingido; tente em instantes.") from e
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Erro da API ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise RuntimeError("Sem conexão com a API da Anthropic.") from e

    if msg.stop_reason == "refusal":
        raise RuntimeError("O modelo recusou a análise deste documento.")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("Resposta truncada (documento extenso). Tente enviar só o edital e o TR.")
    texto = "".join(b.text for b in msg.content if b.type == "text")
    resultado = json.loads(texto)
    resultado["_uso"] = {"entrada": msg.usage.input_tokens, "saida": msg.usage.output_tokens}
    return resultado
