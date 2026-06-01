import pandas as pd
import json
from pathlib import Path

# Raiz do projeto (este script vive em src/); a saída vai para data/
ROOT = Path(__file__).resolve().parent.parent

# 1. URL direta do CSV fornecido na tarefa
csv_url = "https://raw.githubusercontent.com/alvaroriz/datascience_datasets/refs/heads/main/Catalogo-Produtos.csv"

print("Baixando e lendo o CSV...")
# Lê o CSV (ajustando o separador padrão de arquivos fiscais)
df = pd.read_csv(csv_url, sep=';', encoding='utf-8')

# Função auxiliar para limpar NaN e valores vazios
def clean_val(val):
    if pd.isna(val):
        return None
    if isinstance(val, str):
        return val.strip()
    return val

chunks_gerados = []

print("Gerando os chunks com payload tributário completo...")

for index, row in df.iterrows():

    # Extrair chaves principais para a busca semântica
    codigo_sap = str(clean_val(row.get('CÓDIGO SAP', '')))
    apresentacao = clean_val(row.get('APRESENTAÇÃO', ''))
    principio_ativo = clean_val(row.get('PRINCIPIO ATIVO', ''))
    ean = str(clean_val(row.get('CÓDIGO EAN', '')))
    familia = clean_val(row.get('FAMÍLIA', ''))
    tipo_med = clean_val(row.get('TIPO DE MEDICAMENTO', ''))

    # Ignorar linhas inválidas
    if not codigo_sap or not apresentacao:
        continue

    # O texto que a LLM vai ler para achar o produto
    page_content = f"Apresentação: {apresentacao}. Princípio Ativo: {principio_ativo}. Código SAP: {codigo_sap}. Código EAN: {ean}. Família: {familia}. Tipo: {tipo_med}."

    # Função para garantir que impostos virem números (float) em vez de strings
    def to_float(val):
        try:
            if pd.isna(val): return 0.0
            if isinstance(val, str):
                val = val.replace('%', '').replace(',', '.').strip()
            return float(val)
        except:
            return 0.0

    # O payload oculto que o n8n vai usar para a matemática
    metadata = {
        "codigo_sap": codigo_sap,
        "apresentacao": apresentacao,
        "registro_ms": clean_val(row.get('REGISTRO MS')),
        "ncm": clean_val(row.get('NCM (CLASS FISCAL)')),
        "pis_perc": to_float(row.get('% Pis')),
        "cofins_perc": to_float(row.get('% Cofins')),

        # --- CARGA TRIBUTÁRIA COMPLETA (ICMS) ---
        "icms_0_pf": to_float(row.get('ICMS 0 % (PF)')),
        "icms_0_pmc": to_float(row.get('ICMS 0 % (PMC)')),

        "icms_12_pf": to_float(row.get('ICMS 12 %  (PF)')),
        "icms_12_pmc": to_float(row.get('ICMS 12 % (PMC) ')),

        "icms_17_pf": to_float(row.get('ICMS 17 % (PF)')),
        "icms_17_pmc": to_float(row.get('ICMS 17 % (PMC)')),

        "icms_17_5_pf": to_float(row.get('ICMS 17,5 % (PF)')),
        "icms_17_5_pmc": to_float(row.get('ICMS 17,5 % (PMC)')),

        "icms_18_pf": to_float(row.get('ICMS 18 %  (PF)')),
        "icms_18_pmc": to_float(row.get('ICMS 18 %  (PMC)')),

        "icms_20_pf": to_float(row.get('ICMS 20 % (PF)')),
        "icms_20_pmc": to_float(row.get('ICMS 20 % (PMC)')),

        # --- ICMS ÁREAS DE LIVRE COMÉRCIO (ALC) ---
        "icms_17_alc_ac_rr_pf": to_float(row.get('ICMS 17 % (ALC) AC/RR (PF)')),
        "icms_17_alc_ac_rr_pmc": to_float(row.get('ICMS 17 % (ALC) AC/RR (PMC)')),

        "icms_17_5_alc_ro_pf": to_float(row.get('ICMS 17,5 % (ALC) RO (PF)')),
        "icms_17_5_alc_ro_pmc": to_float(row.get('ICMS 17,5 % (ALC) RO (PMC)')),

        "icms_18_alc_am_ap_pf": to_float(row.get('ICMS 18 % (ALC) AM/AP (PF)')),
        "icms_18_alc_am_ap_pmc": to_float(row.get('ICMS 18 % (ALC) AM/AP (PMC)'))
    }

    # Estruturar o objeto final
    chunk_doc = {
        "id": f"sap_{codigo_sap}",
        "page_content": page_content,
        "metadata": metadata
    }

    chunks_gerados.append(chunk_doc)

# Salvar o resultado em data/
output_file = ROOT / "data" / "chunks_hibridos_catalogo_completo.json"
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(chunks_gerados, f, ensure_ascii=False, indent=2)

print(f"Sucesso! {len(chunks_gerados)} chunks gerados e salvos em '{output_file}'.")