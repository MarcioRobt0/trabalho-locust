#!/bin/bash
# =============================================================================
# Trabalho 06 — Script de automação dos experimentos com Locust
# =============================================================================
# Executa: 2 perfis × 3 cenários × 10 repetições = 60 execuções
# Duração por execução: 7 min (1 min warmup + 6 min coleta)
# O aquecimento é descartado na análise (script analyze.py)
#
# CHECKPOINT / RESUME:
#   O script verifica se o CSV de cada execução já existe.
#   Se existir, a execução é pulada automaticamente.
#   Para retomar após interrupção, basta executar o script novamente.
#   Para refazer uma execução específica, apague o CSV correspondente:
#     rm results/csv/ReadProfile_A_leve_rep3_stats.csv
# =============================================================================

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
SKIPPED=0
EXECUTED=0

echo "============================================================"
echo " Trabalho 06 — Avaliação de Desempenho com Locust"
echo " Host: $HOST"
echo " Total de execuções: $TOTAL"
echo " Duração por execução: $((TOTAL_DURATION / 60)) min"
echo " Modo: CHECKPOINT ATIVO (execuções já concluídas são puladas)"
echo "============================================================"
echo ""

for PROFILE in "${PROFILES[@]}"; do
  for SCENARIO in "${SCENARIO_ORDER[@]}"; do
    USERS=${SCENARIOS[$SCENARIO]}

    for i in $(seq 1 $REPETITIONS); do
      CURRENT=$((CURRENT + 1))
      OUTPUT="${RESULTS_DIR}/${PROFILE}_${SCENARIO}_rep${i}"
      CHECKPOINT_FILE="${OUTPUT}_stats.csv"

      # --- CHECKPOINT: pula se o CSV já existe e não está vazio ---
      if [ -f "$CHECKPOINT_FILE" ] && [ -s "$CHECKPOINT_FILE" ]; then
        echo "[$CURRENT/$TOTAL] ⏭️  PULANDO (já concluído): Perfil=$PROFILE | Cenário=$SCENARIO | Rep=$i"
        SKIPPED=$((SKIPPED + 1))
        continue
      fi

      echo "[$CURRENT/$TOTAL] ▶️  Executando: Perfil=$PROFILE | Cenário=$SCENARIO | Usuários=$USERS | Rep=$i"
      echo "  Saída: $OUTPUT"

      # Garante que não há CSV parcial de uma execução anterior interrompida
      rm -f "${OUTPUT}"_*.csv

      # --- Coleta de CPU em background durante a execução ---
      CPU_OUTPUT="${RESULTS_DIR}/docker_stats_${PROFILE}_${SCENARIO}_rep${i}.csv"
      echo "name,cpu_pct,mem_usage,profile,scenario,rep,timestamp" > "$CPU_OUTPUT"
      (
        while true; do
          docker stats --no-stream \
            customers-service api-gateway vets-service visits-service \
            --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" \
            2>/dev/null | while IFS= read -r line; do
              echo "${line},${PROFILE},${SCENARIO},${i},$(date +%s)"
            done
          sleep 5
        done
      ) &
      CPU_PID=$!

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

      # Para a coleta de CPU
      kill "$CPU_PID" 2>/dev/null
      wait "$CPU_PID" 2>/dev/null

      # Verifica se o CSV foi gerado corretamente
      if [ -f "$CHECKPOINT_FILE" ] && [ -s "$CHECKPOINT_FILE" ]; then
        echo "  ✅ Concluído e salvo: $CHECKPOINT_FILE"
        EXECUTED=$((EXECUTED + 1))
      else
        echo "  ⚠️  ATENÇÃO: CSV não foi gerado! Verifique erros acima."
      fi

      # Pausa entre execuções para estabilizar os serviços
      REMAINING=$((TOTAL - CURRENT))
      if [ "$REMAINING" -gt 0 ]; then
        echo "  ⏳ Aguardando 15s (restam $REMAINING execuções)..."
        sleep 15
      fi
    done
  done
done

echo ""
echo "============================================================"
echo " Resumo final:"
echo "   Total planejado : $TOTAL"
echo "   Executadas agora: $EXECUTED"
echo "   Puladas (já ok) : $SKIPPED"
echo "   Pendentes       : $((TOTAL - SKIPPED - EXECUTED))"
echo " Resultados em: $RESULTS_DIR"
echo "============================================================"
