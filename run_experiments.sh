#!/bin/bash
# =============================================================================
# Trabalho 06 — Script de automação dos experimentos com Locust
# =============================================================================
# Executa: 2 perfis × 3 cenários × 10 repetições = 60 execuções
# Duração por execução: 7 min (1 min warmup + 6 min coleta)
# O aquecimento é descartado na análise (script analyze.py)
# =============================================================================

set -e

HOST="${HOST:-http://localhost:8080}"
REPETITIONS=10
TOTAL_DURATION=420   # 7 minutos = 1 min warmup + 6 min coleta (em segundos)
SPAWN_RATE=10
RESULTS_DIR="results/csv"

mkdir -p "$RESULTS_DIR"

# Perfis disponíveis no locustfile.py
PROFILES=("ReadProfile" "WriteProfile")

# Cenários: nome → número de usuários
declare -A SCENARIOS
SCENARIOS["A_leve"]=30
SCENARIOS["B_moderado"]=80
SCENARIOS["C_elevado"]=150

SCENARIO_ORDER=("A_leve" "B_moderado" "C_elevado")

TOTAL=$((${#PROFILES[@]} * ${#SCENARIO_ORDER[@]} * REPETITIONS))
CURRENT=0

echo "============================================================"
echo " Trabalho 06 — Avaliação de Desempenho com Locust"
echo " Host: $HOST"
echo " Total de execuções: $TOTAL"
echo " Duração por execução: $((TOTAL_DURATION / 60)) min"
echo "============================================================"
echo ""

for PROFILE in "${PROFILES[@]}"; do
  for SCENARIO in "${SCENARIO_ORDER[@]}"; do
    USERS=${SCENARIOS[$SCENARIO]}

    for i in $(seq 1 $REPETITIONS); do
      CURRENT=$((CURRENT + 1))
      OUTPUT="${RESULTS_DIR}/${PROFILE}_${SCENARIO}_rep${i}"

      echo "[$CURRENT/$TOTAL] Perfil=$PROFILE | Cenário=$SCENARIO | Usuários=$USERS | Rep=$i"
      echo "  Saída: $OUTPUT"

      locust \
        -f locustfile.py \
        --headless \
        --users "$USERS" \
        --spawn-rate "$SPAWN_RATE" \
        --run-time "${TOTAL_DURATION}s" \
        --host "$HOST" \
        --csv "$OUTPUT" \
        --csv-full-history \
        --only-summary \
        --class-picker "$PROFILE" \
        2>&1 | grep -E "^\[|Aggregated|Exception" || true

      echo "  ✅ Concluído"

      # Pausa entre execuções para estabilizar os serviços
      if [ "$CURRENT" -lt "$TOTAL" ]; then
        echo "  ⏳ Aguardando 15s antes da próxima execução..."
        sleep 15
      fi
    done
  done
done

echo ""
echo "============================================================"
echo " ✅ Todas as $TOTAL execuções concluídas!"
echo " Resultados em: $RESULTS_DIR"
echo "============================================================"
