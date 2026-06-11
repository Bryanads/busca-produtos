## Bryan Santos, Gustavo Salvador, Julia Curto e Luã Macedo
# Orçamento Farmacêutico Híbrido — AP2

Sistema profissional de **orçamentação com RAG**: uma API recebe uma solicitação de orçamento
(linguagem natural), encontra os medicamentos no catálogo por **busca híbrida** (semântica + lexical,
fundidas por RRF) e devolve um **orçamento estruturado em JSON** gerado com apoio de uma LLM local.

> 📦 **Entregáveis** na pasta [`entregaveis/`](entregaveis/): os 2 fluxos n8n, a documentação em
> PDF e as requisições de teste em curl.

## Arquitetura em dois workflows n8n

**Ingestão — [`entregaveis/wf_ingestao.json`](entregaveis/wf_ingestao.json)** (offline, roda uma vez):
baixa o CSV do catálogo → gera um *chunk* por produto → embeddings (LM Studio) → upsert na tabela
`documents` (Supabase/pgvector). Disparo por *Manual Trigger*.

**Consulta — [`entregaveis/wf_consulta.json`](entregaveis/wf_consulta.json)** (online, a cada pedido):
`Webhook POST` → busca híbrida + RRF → LLM → **Respond to Webhook** com o JSON do orçamento.
Tratamento de erros por etapa (503 IA · 502 banco · 500 interno).

```
.
├── entregaveis/             # ENTREGÁVEIS do AP2
│   ├── wf_ingestao.json     #   fluxo de ingestão (n8n)
│   ├── wf_consulta.json     #   fluxo de consulta (n8n)
│   ├── documentacao-ap2.pdf #   documentação profissional
│   └── requisicoes.sh       #   os 10 casos do enunciado em curl
├── sql/setup.sql            # extensão pgvector, tabela documents, índices (recriar o banco)
└── docs/documentacao-ap2.html  # fonte HTML da documentação
```

## Estrutura da resposta (contrato da API)

```json
{
  "status": "200",
  "orcamento": [
    { "item_solicitado": "ACCUVIT", "item_catalogo": "ACCUVIT COMREV FRX30",
      "item_preco": 125.24, "item_quantidade": 3, "icms": 18 }
  ],
  "total_orcamento": 375.72,
  "obs": "Preco utilizado: ICMS 18% PMC."
}
```

| status | quando |
| ------ | ------ |
| `200`  | orçamento gerado |
| `400`  | solicitação vazia ou inválida |
| `404`  | produto fora da base |
| `422`  | solicitação ambígua (ex.: mesma droga em dosagens diferentes, sem especificar) |
| `502`  | banco de dados indisponível / erro de SQL |
| `503`  | serviço de IA indisponível (embeddings ou LLM) |
| `500`  | erro interno (ex.: resposta do modelo ilegível) |

O **tratamento de erro é por etapa**: cada nó de I/O desvia para uma etiqueta que carimba a etapa e
o status apropriado, convergindo no nó central `Tratar Erro`. A resposta de erro inclui `etapa` e
`componente` para diagnóstico (veja a "aba de erros" — sticky vermelho — no canvas do n8n).

O **fluxo de ingestão** segue o mesmo padrão: download do CSV, geração de chunks, embedding e upsert
têm cada um seu `onError` → etiqueta → `Tratar Erro Ingestao`, que monta um relatório e dispara
**Stop and Error** — travando a ingestão com diagnóstico claro, sem falha silenciosa.

## Pré-requisitos

- **n8n** (testado no Docker local em `localhost:5678`).
- **LM Studio** local com dois modelos carregados:
  - embedding `text-embedding-bge-m3` (1024 dimensões);
  - chat `gemma-3n-e4b-it-text`.
- Projeto **Supabase** (PostgreSQL com a extensão `vector`) e a credencial Postgres configurada no n8n.

> Os nós HTTP apontam para `http://172.17.0.1:1234` — o host visto de dentro do container do n8n.
> Como o n8n e o LM Studio rodam na mesma máquina, nada precisa ser exposto à internet.

## Como importar e ativar os workflows

```bash
# Importar no n8n local (via container Docker chamado "n8n"):
for f in wf_ingestao wf_consulta; do
  docker cp entregaveis/$f.json n8n:/tmp/ && docker exec n8n n8n import:workflow --input=/tmp/$f.json
done
# Ativar o de consulta (reiniciar registra o webhook de produção):
docker exec n8n n8n update:workflow --id=ap2consultaWF0001 --active=true && docker restart n8n
```
Ou, pela interface: **n8n → Import from File**, configure a credencial Postgres `supabase` e ative
o fluxo de consulta.

## Como rodar a ingestão

Abra o workflow **AP2 - Ingestao do Catalogo** no n8n e clique no *Manual Trigger*. Ele baixa o CSV,
gera os ~981 chunks, calcula os embeddings e faz upsert em `documents` (idempotente via `chunk_id`).
Só é necessário se o banco estiver vazio — na entrega, a base já está populada.

## Como testar a consulta

```bash
# 1 chamada
curl -X POST http://localhost:5678/webhook/orcamento \
  -H "Content-Type: application/json" \
  -d '{"email":"Preciso de 3 unidades de ACCUVIT."}'

# Os 10 casos do enunciado em curl:
bash entregaveis/requisicoes.sh
```

## Diferenciais implementados

- **Busca híbrida (vetorial + lexical) + RRF + re-ranking** — fusão das duas buscas com boost lexical.
- **Resolução determinística (menos IA)** — código SAP entra por regra; quantidades corrigidas por
  proximidade no texto, desambiguando produtos de mesmo nome pela dosagem.
- **Sinônimos e variações de nome** — ex.: "herpes" → aciclovir; abreviações de forma (comprimido→COM…).
- **Cache de consultas** — pedidos idênticos respondem em ~0,02 s (vs ~4,5 s). Só respostas `200`.
- **Logs estruturados + métricas** — nó `Registrar Log` (JSON por requisição) na aba de execuções.
- **Tratamento de erro por etapa** — cada falha técnica retorna o status condizente (503 IA, 502 banco,
  500 interno) com `etapa`/`componente` para diagnóstico.
- **Ingestão otimizada** — embeddings por chunk, mas **um único upsert em massa** (transação) no fim.

## ⚠️ Segurança

- O arquivo `.env` está no `.gitignore` e **não deve ser commitado** — ele contém a
  `SUPABASE_SERVICE_KEY`. Se a chave já tiver sido exposta, **rotacione-a** no painel do Supabase.
