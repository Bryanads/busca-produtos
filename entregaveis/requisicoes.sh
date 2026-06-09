#!/usr/bin/env bash
# Requisicoes de exemplo para a API de orcamento (AP2).
# Cada bloco envia um caso via POST ao webhook e imprime a resposta JSON.
# Uso:  bash entregaveis/requisicoes.sh
#       BASE_URL=http://localhost:5678 bash entregaveis/requisicoes.sh

BASE="${BASE_URL:-http://localhost:5678}/webhook/orcamento"

echo "== Caso 01 - Pedido pelo nome comercial =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Preciso de 3 unidades de ACCUVIT."}'
echo -e "\n"

echo "== Caso 02 - Pedido pelo codigo SAP =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Favor cotar 5 unidades do codigo 1003649."}'
echo -e "\n"

echo "== Caso 03 - Principio ativo e dosagem =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Gostaria de orcamento para 2 unidades de acetilcisteina 40mg xarope."}'
echo -e "\n"

echo "== Caso 04 - Erro de digitacao =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Quero 4 unidades de acetilsisteina 20mg."}'
echo -e "\n"

echo "== Caso 05 - Apresentacao especifica =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Me envie orcamento de 6 unidades de Acheflan creme bisnaga de 30g."}'
echo -e "\n"

echo "== Caso 06 - Multiplos itens =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Preciso cotar:\n2 unidades de ACICLOVIR 200MG\n3 unidades de ACICLOVIR creme 50mg\n1 unidade de ACHEFLAN aerosol"}'
echo -e "\n"

echo "== Caso 07 - Misturando codigo e nome =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Cotar 2 unidades do codigo 1005119 e 3 unidades de acido mefenamico 500mg."}'
echo -e "\n"

echo "== Caso 08 - Pedido informal =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Oi, consegue ver pra mim 10 caixas daquele remedio de herpes, aciclovir comprimido?"}'
echo -e "\n"

echo "== Caso 09 - Produto ambiguo =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Preciso de 5 unidades de ACEBROFILINA."}'
echo -e "\n"

echo "== Caso 10 - Produto fora da base =="
curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" \
  -d '{"email": "Preciso de 2 unidades de miojo."}'
echo -e "\n"

echo "== (erro de negocio) Entrada vazia -> status 400 =="
curl -s -X POST "$BASE" -H "Content-Type: application/json" -d '{"email":""}'
echo -e "\n"
