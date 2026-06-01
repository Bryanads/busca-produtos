-- Rode este SQL no Supabase (SQL Editor) antes da ingestão.
-- Cria a extensão pgvector, a tabela `documents` no padrão esperado pelo
-- nó "Supabase Vector Store" do n8n, e a função match_documents para busca.

create extension if not exists vector;

create table if not exists documents (
  id          bigserial primary key,
  chunk_id    text unique,
  content     text not null,
  metadata    jsonb not null default '{}'::jsonb,
  embedding   vector(1024)
);

create index if not exists documents_embedding_hnsw
  on documents using hnsw (embedding vector_cosine_ops);

create index if not exists documents_metadata_codigo_sap
  on documents ((metadata->>'codigo_sap'));

create or replace function match_documents (
  query_embedding vector(1024),
  match_count     int default 5,
  filter          jsonb default '{}'::jsonb
) returns table (
  id         bigint,
  content    text,
  metadata   jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    d.id,
    d.content,
    d.metadata,
    1 - (d.embedding <=> query_embedding) as similarity
  from documents d
  where d.metadata @> filter
  order by d.embedding <=> query_embedding
  limit match_count;
end;
$$;
