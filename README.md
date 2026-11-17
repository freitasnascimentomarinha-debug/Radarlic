# 📡 RadarLic — inteligência para vender ao governo

Sistema em **Streamlit** para empresas que vendem à administração pública: encontra editais
abertos e futuros, ranqueia as melhores oportunidades, lê o edital com IA, mostra o preço
histórico de cada item, quem são os concorrentes e calcula o preço de lance.

Tudo com **dados abertos oficiais** (PNCP e Compras.gov.br), sem raspagem de site e sem custo
de API (exceto a IA, opcional).

---

## 1. O que o empresário de licitação faz (e onde o sistema ajuda)

| Etapa do dia a dia | Dor típica | Tela do RadarLic |
|---|---|---|
| **Prospecção** – achar editais do seu ramo entre milhares por dia | Perde dispensas de 3 dias; lê editais que não servem | 🎯 **Radar** (pregões, dispensas, concorrências abertos e *a abrir*, com score) |
| **Antecipação** – saber o que o órgão vai comprar antes do edital | Descobre o edital tarde, sem fornecedor negociado | 🗓️ **Compras futuras (PCA)** |
| **Triagem do edital** – ler 60–150 páginas para saber se dá para participar | Horas por edital; perde exigência escondida (atestado, amostra) | 📄 **Análise com IA** (exigências, prazos, riscos, cláusulas restritivas, checklist, nota de viabilidade) |
| **Escolha** – entre vários editais, onde vale a pena | Decide no feeling | ⚖️ **Comparar editais** |
| **Precificação** – saber quanto o governo paga e quanto consigo dar | Erra o markup (aplica % sobre custo), dá lance inexequível | 💰 **Preços históricos** + 🧮 **Calculadora de margem** |
| **Inteligência competitiva** – quem ganha, a que preço, para quem | Não conhece o rival da disputa | 🏆 **Concorrentes** (ranking do ramo + raio-X do CNPJ com todos os itens ganhos) |
| **Gestão** – carteira de editais, perfil, histórico | Planilhas soltas | 🏢 **Perfil e carteira** (export/import JSON) |

Ferramentas comerciais do mercado (ConLicitação, Effecti, Siga Pregão etc.) cobram mensalidade
por esse mesmo pacote: boletim de editais, análise de concorrência, preços praticados, robô de
lance e gestão de documentos.

### Avaliação das suas ideias originais
- **Preço médio/mínimo/máximo histórico** ✅ — implementado. Detalhe que faz diferença: separar por
  **unidade de fornecimento** (resma × caixa com 10 resmas) e descartar preços discrepantes, como
  orienta a IN SEGES 65/2021. "Mínimo médio" = média dos menores preços de cada mês (é o preço
  que costuma vencer).
- **Dispensas e pregões abertos e a abrir** ✅ — o Radar separa *Aberto* / *A abrir* e dispensas.
  Dispensa eletrônica tem prazo curto (em geral 3 dias úteis) e menos concorrência: é onde
  empresa pequena começa a ganhar.
- **Resumo do edital com IA** ✅ — com saída estruturada, não um texto livre: isso permite o
  comparador e o checklist.
- **Calculadora de margem** ✅ — por *markup divisor* (impostos sobre o preço), com lance mínimo,
  ponto de equilíbrio, alerta de inexequibilidade (75% da referência) e tabela de lances.
- **Concorrentes** ✅ — ranking por item/ramo, clique para ver todos os itens que a empresa forneceu.

### O que acrescentei
1. **Score de oportunidade (0–100)** com explicação (aderência, prazo, valor, UF, competição, ME/EPP).
2. **Compras futuras pelo PCA**: o sinal mais antecipado de demanda.
3. **Descobridor de CATMAT por texto** (a API oficial não tem busca textual no catálogo).
4. **Cláusulas possivelmente restritivas** na análise da IA → base para esclarecimento/impugnação.
5. **Raio-X do concorrente**: porte, capital, sócios, CNAE (Receita) + faturamento com governo.

### Versão 2 — gestão completa e visual moderno
| Tela | O que faz |
|---|---|
| 🏠 **Painel** | Página inicial: disputas dos próximos 7 dias (linha do tempo), funil, taxa de vitória, valor ganho, certidões a renovar e atalhos. |
| 📊 **Funil de propostas** | Cada edital salvo passa por Triagem → Cotando → Proposta enviada → Em disputa → Ganho/Perdido. Edição direto na tabela (status, valor da proposta, responsável, anotações), gráfico de conversão e valor por status. |
| 📅 **Agenda de disputas** | Calendário (FullCalendar, JavaScript) com sessões e vencimento de certidões; exporta `.ics` para Google Agenda/Outlook com lembrete 1 dia antes. |
| 🛡️ **Certidões e habilitação** | Validade de CND federal, FGTS, CNDT, estadual, municipal, falência, balanço, SICAF e CEIS/CNEP, com semáforo e link para emitir. |
| 📝 **Proposta e petições** | Gera a **proposta comercial em Word** com os itens do edital (marca, modelo, preço) e os dados da empresa; redige **pedido de esclarecimento ou impugnação** com IA a partir da análise do edital (art. 164). |
| 🤝 **Atas e carona (ARP)** | Atas vigentes do item: preço registrado, detentor, limite para adesões (art. 86) e atas **vencendo em 90 dias** (o órgão vai licitar de novo). |
| 🎲 **Chance de vencer** | Na calculadora: probabilidade empírica de vencer a cada preço (a partir dos preços homologados) e **preço ótimo** que maximiza chance × lucro, respeitando uma chance mínima. |
| 🔔 **Alertas automáticos** | `scripts/alerta.py` + GitHub Actions: todo dia útil às 07:17 busca editais novos com o seu perfil e envia os de score alto por **Telegram** e/ou **e-mail**. |

**Tabelas:** todas usam AG Grid (JavaScript) com formato brasileiro (R$, datas), selos coloridos,
barra de score, contagem regressiva do prazo, busca, filtros por coluna, paginação, colunas fixas,
exportação e edição em linha. **Cartões de indicadores** animados e **tema** próprio (fonte Inter,
barra lateral escura, gráficos padronizados).

### Próximos passos sugeridos
- **Banco persistente** (Supabase ou Google Sheets) no lugar do JSON, para uso em equipe.
- **Contratos vencendo** por órgão (`modulo-contratos/1.2_consultarContratos_FimVigencia`).
- **Cotação com fornecedores**: enviar pedido de cotação por e-mail a partir dos itens do edital.

---

## 2. Fontes de dados (testadas em 17/11/2026)

| Dado | Endpoint |
|---|---|
| Busca de editais (texto, UF, modalidade, situação) | `https://pncp.gov.br/api/search/` |
| Itens, resultados e arquivos da contratação | `https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/...` |
| Detalhe da contratação | `https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}` |
| Preços praticados (CATMAT/CATSER) | `dadosabertos.compras.gov.br/modulo-pesquisa-preco/1_consultarMaterial` · `3_consultarServico` |
| Catálogo de materiais | `dadosabertos.compras.gov.br/modulo-material/4_consultarItemMaterial` |
| Itens ganhos por fornecedor (Lei 14.133) | `dadosabertos.compras.gov.br/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133` |
| Plano de Contratações Anual | `dadosabertos.compras.gov.br/modulo-pgc/2_consultarPgcDetalheCatalogo` |
| Cadastro de CNPJ | `https://brasilapi.com.br/api/cnpj/v1/{cnpj}` |

**Atenção:** as APIs do governo oscilam (respostas vazias, HTTP 500, lentidão de 50 s). O
`core/http.py` faz retentativas com espera progressiva, cada consulta tem cache próprio e o Radar
mostra quais buscas falharam sem descartar as que deram certo.

---

## 3. Rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # coloque sua ANTHROPIC_API_KEY
streamlit run app.py
```

A chave da Anthropic só é necessária para a **análise de edital com IA**
(crie em https://console.anthropic.com). O restante funciona sem chave.

## 4. Alertas automáticos (Telegram / e-mail)

1. Edite `alertas/perfil.json` (palavras-chave, UFs, faixa de valor, ME/EPP) — ou copie o bloco
   `perfil` do JSON exportado em **Meu perfil → Exportar carteira**.
2. **Telegram:** fale com `@BotFather`, crie um bot e copie o token; mande uma mensagem ao bot e
   pegue seu `chat_id` em `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. No GitHub: **Settings → Secrets and variables → Actions** → crie `TELEGRAM_TOKEN` e
   `TELEGRAM_CHAT_ID` (e/ou `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_TO`).
   Opcional: variável `SCORE_MIN` (padrão 60).
4. O workflow `.github/workflows/alertas.yml` roda nos dias úteis às 07:17 (Brasília). Para testar,
   vá em **Actions → Alertas RadarLic → Run workflow**. O workflow só roda a partir do branch padrão.

## 5. Publicar no Streamlit Community Cloud

1. Suba este repositório no GitHub (pode ser privado).
2. Em https://share.streamlit.io → **Create app** → escolha o repositório, branch e `app.py`.
3. Em **Advanced settings → Secrets**, cole:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   APP_PASSWORD = "uma-senha"   # opcional: protege o app publicado
   ```
4. Deploy. O disco do Streamlit Cloud é apagado quando o app reinicia: use **Meu perfil →
   Exportar carteira** para guardar perfil, editais salvos e análises.

---

## 6. Estrutura

```
app.py                 navegação, senha opcional
core/http.py           cliente HTTP com retentativa
core/pncp.py           busca de editais, itens, arquivos
core/compras.py        preços praticados, catálogo, vencedores, PCA, descobridor de CATMAT
core/cnpj.py           cadastro de CNPJ
core/scoring.py        score de oportunidade
core/pricing.py        formação de preço (markup divisor)
core/ia.py             análise de edital com Claude (saída JSON estruturada)
core/storage.py        perfil, funil, certidões (JSON)
core/theme.py          tema, cabeçalhos, cartões animados (JS), template Plotly
core/grid.py           tabelas AG Grid (JS): formatos, selos, prazos, edição
core/docs.py           proposta e petições (.docx), agenda (.ics)
scripts/alerta.py      alerta diário (GitHub Actions)
views/*.py             uma tela por arquivo
```

## 7. Base legal citada no sistema
Lei 14.133/2021 (arts. 9º, 12, 23, 41, 59, 62–70, 75, 86, 87, 96–98, 164) · LC 123/2006 (arts. 44 e 48) ·
IN SEGES 65/2021 (pesquisa de preços) · IN SEGES 73/2022 · Decreto 11.462/2023.
A análise de IA serve para **triagem**: confirme sempre no texto do edital.
