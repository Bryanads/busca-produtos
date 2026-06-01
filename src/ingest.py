"""Gera embeddings via LM Studio e faz upsert na tabela `documents` do Supabase."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import create_client
from tqdm import tqdm


def env(key: str, default: str | None = None, required: bool = False) -> str:
    val = os.getenv(key, default)
    if required and not val:
        sys.exit(f"[erro] variável de ambiente {key} não definida (veja .env.example)")
    return val  # type: ignore[return-value]


def embed_batch(client: httpx.Client, base_url: str, model: str, texts: list[str]) -> list[list[float]]:
    resp = client.post(
        f"{base_url}/embeddings",
        json={"model": model, "input": texts},
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    # LM Studio devolve na ordem da entrada, mas garantimos por `index`
    data.sort(key=lambda x: x["index"])
    return [item["embedding"] for item in data]


def main() -> None:
    load_dotenv()

    base_url = env("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    model = env("LMSTUDIO_MODEL", required=True)
    expected_dim = int(env("EMBEDDING_DIM", "1024"))
    supabase_url = env("SUPABASE_URL", required=True)
    supabase_key = env("SUPABASE_SERVICE_KEY", required=True)
    input_path = Path(env("INPUT_JSON", "data/chunks_hibridos_catalogo_completo.json"))
    table = env("TABLE_NAME", "documents")
    batch_size = int(env("BATCH_SIZE", "32"))

    # Resolve caminhos relativos a partir da raiz do projeto (este script vive em src/)
    if not input_path.is_absolute():
        input_path = Path(__file__).resolve().parent.parent / input_path

    if not input_path.exists():
        sys.exit(f"[erro] JSON não encontrado: {input_path.resolve()}")

    chunks = json.loads(input_path.read_text(encoding="utf-8"))
    print(f"[info] carregados {len(chunks)} chunks de {input_path.name}")

    supabase = create_client(supabase_url, supabase_key)
    http = httpx.Client()

    # Sanity check: confere a dimensão do modelo num único texto antes de processar tudo
    probe = embed_batch(http, base_url, model, [chunks[0]["page_content"]])
    got_dim = len(probe[0])
    if got_dim != expected_dim:
        sys.exit(
            f"[erro] dimensão do modelo ({got_dim}) difere de EMBEDDING_DIM ({expected_dim}). "
            f"Atualize EMBEDDING_DIM e o vector(N) em setup.sql para bater."
        )
    print(f"[info] modelo '{model}' devolveu vetor de {got_dim}d — OK")

    total = 0
    for start in tqdm(range(0, len(chunks), batch_size), desc="embeddings"):
        batch = chunks[start : start + batch_size]
        texts = [c["page_content"] for c in batch]
        vectors = embed_batch(http, base_url, model, texts)

        rows = [
            {
                "chunk_id": c["id"],
                "content": c["page_content"],
                "metadata": c["metadata"],
                "embedding": vec,
            }
            for c, vec in zip(batch, vectors)
        ]
        supabase.table(table).upsert(rows, on_conflict="chunk_id").execute()
        total += len(rows)

    print(f"[ok] {total} linhas upsertadas em {table}")


if __name__ == "__main__":
    main()
