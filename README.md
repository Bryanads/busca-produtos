## Bryan Santos, Gustavo Salvador e Julia Curto
# Orçamento Farmacêutico Híbrido

Pipeline de **RAG** (Retrieval-Augmented Generation) que lê um e-mail de solicitação de
orçamento, encontra os medicamentos no catálogo usando **busca híbrida** (semântica + lexical
fundidas por RRF) e devolve um **orçamento estruturado em JSON** gerado por uma LLM local.

> 📄 Para a explicação visual completa do fluxo, abra
> [`docs/fluxo-orcamento-farmaceutico-hibrido.html`](docs/fluxo-orcamento-farmaceutico-hibrido.html)
> no navegador.

## Arquitetura em duas fases

**Offline (indexação — roda uma vez):**

1. `src/build_chunks.py` — baixa o CSV do catálogo e gera um *chunk* por produto.
2. `sql/setup.sql` — cria a tabela `documents` com pgvector no Supabase/Postgres.
3. `src/ingest.py` — gera os embeddings (LM Studio) e popula o banco.

**Online (consulta — roda a cada e-mail):**

4. `n8n/orcamento-farmaceutico-hibrido.json` — workflow do n8n que faz a busca híbrida,
   funde os resultados com RRF e chama a LLM para montar o orçamento.

## Estrutura do repositório

```
.
├── src/
│   ├── build_chunks.py   # CSV do catálogo  ->  data/chunks_*.json
│   └── ingest.py         # chunks + embeddings  ->  tabela documents (Supabase)
├── sql/
│   └── setup.sql         # extensão pgvector, tabela documents, índices, match_documents()
├── data/
│   └── chunks_hibridos_catalogo_completo.json   # 981 chunks (gerado por build_chunks.py)
├── n8n/
│   └── orcamento-farmaceutico-hibrido.json      # workflow n8n (importar no n8n)
├── docs/
│   └── fluxo-orcamento-farmaceutico-hibrido.html # documentação do fluxo
├── requirements.txt
└── .env.example
```

## Pré-requisitos

- **Python 3.10+**
- **LM Studio** rodando localmente com:
  - um modelo de **embedding** carregado (text-embedding-bge-m3`, 1024 dimensões);
  - um modelo de **chat** para gerar o orçamento (gemma-3n-e4b-it-text).
- Um projeto no **Supabase** (Postgres com a extensão `vector`).
- **n8n** (para executar o workflow de consulta).

## Como rodar a indexação

```bash
# 1. Ambiente Python
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configuração
cp .env.example .env
# edite o .env com a URL/KEY do Supabase e o modelo do LM Studio

# 3. (Opcional) regenerar os chunks a partir do CSV
python src/build_chunks.py

# 4. Criar a tabela no Supabase
#    cole o conteúdo de sql/setup.sql no SQL Editor do Supabase e execute

# 5. Gerar embeddings e popular o banco
python src/ingest.py
```

## Como rodar a consulta

1. No n8n, importe `n8n/orcamento-farmaceutico-hibrido.json`.
2. Configure a credencial Postgres apontando para o seu Supabase.
3. Ajuste a URL do LM Studio nos nós de HTTP (por padrão `http://172.17.0.1:1234`,
   o host visto de dentro do container do n8n).
4. Edite o nó **Email de Teste** com a solicitação e dispare o **Trigger Manual**.

## Variáveis de ambiente

Veja [`.env.example`](.env.example). Resumo:

| Variável               | Descrição                                                        |
| ---------------------- | ---------------------------------------------------------------- |
| `LMSTUDIO_BASE_URL`    | Endpoint do LM Studio (ex.: `http://localhost:1234/v1`)          |
| `LMSTUDIO_MODEL`       | Modelo de embedding (ex.: `bge-m3`)                              |
| `EMBEDDING_DIM`        | Dimensão do vetor — precisa bater com o `vector(N)` no SQL (1024)|
| `SUPABASE_URL`         | URL do projeto Supabase                                          |
| `SUPABASE_SERVICE_KEY` | **Service role key** (insert em massa) — secreta                |
| `INPUT_JSON`           | Caminho do JSON de chunks (`data/chunks_...json`)               |
| `TABLE_NAME`           | Nome da tabela (`documents`)                                     |
| `BATCH_SIZE`           | Lote de textos por requisição de embedding                      |

## ⚠️ Segurança

- O arquivo `.env` está no `.gitignore` e **não deve ser commitado** — ele contém a
  `SUPABASE_SERVICE_KEY`, que dá acesso total ao banco.
- Se a chave de serviço já tiver sido exposta, **rotacione-a** no painel do Supabase
  (Settings → API).
