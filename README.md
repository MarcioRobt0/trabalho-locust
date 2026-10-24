# Trabalho Prático 06: Avaliação de Desempenho com Locust

Repositório com os testes de carga e avaliação de desempenho do **Spring PetClinic Microservices** usando o **Locust**.

---

## Vídeo Demonstrativo
> **Link do Vídeo:** [LINK ]

---

## Ambiente de Testes

Os testes foram rodados localmente com as seguintes configurações:

| Item | Descrição |
|---|---|
| **Sistema Operacional** | Ubuntu 24.04.5 LTS (Kernel Linux 7.0.0-38-generic) |
| **Processador** | 12th Gen Intel Core i5-1235U (10 núcleos, 12 threads) |
| **Memória RAM** | 16 GB |
| **Docker** | Versão 29.9.1 |
| **Docker Compose** | Versão v5.6.0 |
| **Python** | 3.12.3 |
| **Locust** | 2.47.0 |

---

## Arquitetura e Endpoints Testados

A aplicação roda em microsserviços via Docker Compose. Todas as requisições passam pelo **API Gateway** (porta 8080), que faz o roteamento para cada serviço:

- `GET /api/customer/owners`: lista todos os donos (`customers-service`)
- `GET /api/customer/owners/{id}`: busca dono por ID (`customers-service`)
- `GET /api/vet/vets`: lista veterinários (`vets-service`)
- `POST /api/customer/owners`: cadastra novo dono (`customers-service`)

---

## Metodologia dos Experimentos

### 1. Perfis de Carga (`locustfile.py`)

Foram implementados dois perfis de usuários com tempo de espera aleatório entre 1 e 3 segundos:

| Operação | Perfil 1 (Leitura) | Perfil 2 (Escrita) |
|---|:---:|:---:|
| `GET /owners` | 45% | 20% |
| `GET /owners/{id}` | 35% | 20% |
| `GET /vets` | 15% | 20% |
| `POST /owners` | 5% | 40% |

### 2. Cenários e Repetições

Cada perfil foi testado em 3 cenários de usuários simultâneos:

| Cenário | Usuários | Spawn Rate | Duração Total | Aquecimento (descartado) | Medição Real |
|---|:---:|:---:|:---:|:---:|:---:|
| **A: Leve** | 30 | 10 usuários/s | 7 min | 1 min | 6 min |
| **B: Moderado** | 80 | 10 usuários/s | 7 min | 1 min | 6 min |
| **C: Elevado** | 150 | 10 usuários/s | 7 min | 1 min | 6 min |

- **Total:** 2 perfis x 3 cenários x 10 repetições = **60 execuções**.
- **Tratamento dos dados:** O primeiro minuto de cada rodada foi descartado pelo script `analyze.py`, calculando a média e desvio padrão somente dos 6 minutos estáveis.
- **Automação:** O script `run_experiments.sh` executa as rodadas com checkpoint (se o teste for interrompido, continua de onde parou sem perder dados) e grava o uso de CPU via `docker stats` a cada 5 segundos.

---

## Como Reproduzir os Testes

1. Subir o PetClinic:
   ```bash
   cd ../spring-petclinic-microservices
   docker compose up -d
   # Aguarde uns 2 minutos para os containers registrarem no Eureka
   ```

2. Instalar dependências do Python:
   ```bash
   pip install -r requirements.txt
   ```

3. Rodar os testes automatizados:
   ```bash
   chmod +x run_experiments.sh
   ./run_experiments.sh
   ```

4. Processar os resultados e gerar os gráficos:
   ```bash
   python3 analyze.py
   ```

---

## Resultados e Tabelas

### Resumo Geral (Média das 10 repetições)

| Perfil | Cenário | Usuários | Tempo Médio (ms) | P95 (ms) | Vazão (req/s) | Total Requisições | Taxa de Falhas (%) | Desvio Padrão (ms) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Perfil 1 (Leitura)** | A: Leve | 30 | **57.3** | **212.8** | **14.50** | 5.219 | **0.01%** | 56.0 |
| **Perfil 1 (Leitura)** | B: Moderado | 80 | **1788.8** | **4513.9** | **25.74** | 9.265 | **68.98%** | 1993.3 |
| **Perfil 1 (Leitura)** | C: Elevado | 150 | **659.9** | **2642.0** | **59.27** | 21.336 | **75.68%** | 639.1 |
| **Perfil 2 (Escrita)** | A: Leve | 30 | **999.7** | **4011.5** | **10.81** | 3.890 | **75.59%** | 1011.3 |
| **Perfil 2 (Escrita)** | B: Moderado | 80 | **317.0** | **1568.0** | **35.29** | 12.705 | **97.97%** | 72.5 |
| **Perfil 2 (Escrita)** | C: Elevado | 150 | **77.2** | **215.9** | **73.02** | 26.287 | **99.77%** | 76.9 |

---

### Gráficos Comparativos

1. **Tempo de Resposta Médio por Usuários:**  
   ![Tempo de Resposta](results/charts/01_response_time_by_users.png)

2. **Percentil 95 (P95) por Usuários:**  
   ![P95](results/charts/02_p95_by_users.png)

3. **Comparativo de Vazão:**  
   ![Vazão](results/charts/03_throughput_comparison.png)

4. **Taxa de Falhas por Cenário:**  
   ![Taxa de Falhas](results/charts/04_failure_rate.png)

5. **Curva de Evolução do Tempo de Resposta:**  
   ![Evolução](results/charts/05_response_time_progression.png)

6. **Degradação por Operação:**  
   ![Degradação Endpoints](results/charts/06_endpoint_degradation.png)

7. **Consumo de CPU dos Microsserviços:**  
   ![Consumo CPU](results/charts/07_cpu_usage.png)

---

## Respostas às Questões do Trabalho

### 1. Como o aumento de usuários afeta o tempo de resposta?
No Perfil de Leitura, subir de 30 para 80 usuários fez o tempo médio saltar de 57 ms para quase 1.800 ms (mais de 30 vezes maior), e o P95 passou de 212 ms para 4.513 ms. Já com 150 usuários, o tempo médio parece cair para 660 ms, mas isso acontece porque o Circuit Breaker do API Gateway entrou em ação e começou a rejeitar requisições de forma imediata (com erro 503 em menos de 10 ms), o que puxa a média para baixo.

No Perfil de Escrita, como tem muita gravação no banco, o sistema já sofreu com 30 usuários (média de 1.000 ms). Com 80 e 150 usuários o Circuit Breaker abriu quase direto, dando tempo aparente de 77 ms porque quase tudo virou erro rápido.

### 2. Qual perfil apresenta maior vazão?
Em números brutos, o Perfil 2 (Escrita) registrou maior vazão (média de 39.71 req/s contra 33.17 req/s do Perfil 1).

Porém, a maior parte dessa vazão do Perfil 2 foram respostas de erro rápido do Circuit Breaker (com 99.77% de falha no cenário elevado). Se considerarmos apenas requisições que deram certo de verdade (vazão útil ou goodput), o Perfil 1 (Leitura) teve um desempenho bem melhor, conseguindo atender com sucesso a maioria das chamadas no cenário leve e parte no moderado.

### 3. Quais operações apresentam maior degradação?
Comparando o cenário de 30 usuários com o de 150 usuários, o aumento no tempo de resposta (P95) foi:
- `GET /api/customer/owners/{id}`: degradou **14.4x**
- `POST /api/customer/owners`: degradou **12.6x**
- `GET /api/customer/owners`: degradou **12.2x**
- `GET /api/vet/vets`: praticamente estável (**0.67x**, sem degradação)

Os três endpoints de clientes pesaram muito porque batem no `customers-service` e no banco de dados. Já o `/vets` ficou estável porque fica em outro microsserviço isolado (`vets-service`) e usa cache em memória (`@Cacheable`), mostrando que a divisão em microsserviços realmente isolou o problema.

### 4. Como o consumo de CPU varia entre os cenários?
- **customers-service:** Foi o maior gargalo. Ficou em 182% de CPU no cenário Leve e bateu 208% no Moderado, usando múltiplos núcleos por conta de processamento de requisições, JSON e banco. No cenário Elevado a CPU média caiu para 109% porque o Gateway começou a barrar requisições antes de chegarem nele.
- **api-gateway:** O uso de CPU subiu conforme o volume de requisições: 3.5% no Leve, 6.1% no Moderado e 15.4% no Elevado.
- **vets-service:** Ficou abaixo de 1% de CPU o tempo todo (entre 0.4% e 0.9%), graças ao cache.

### 5. Qual cenário apresenta maior taxa de falhas?
O **Cenário C (Elevado, 150 usuários)** teve a maior taxa de falhas, com média geral de **87.72%** (75.68% no perfil de leitura e 99.77% no de escrita).

O Cenário B (80 usuários) teve 83.47% de falhas e o Cenário A (30 usuários) teve 37.80% (quase todas concentradas no perfil de escrita). As falhas foram causadas principalmente pelo Circuit Breaker e pelo esgotamento de conexões com o banco.

---

## Conclusões

1. **Gargalo no Customers Service:** O serviço de clientes foi o limitador de performance da aplicação, principalmente nas operações de cadastro (POST).
2. **Importância do Circuit Breaker:** O mecanismo de proteção do Spring Cloud Gateway evitou que a máquina travasse completamente sob carga pesada, descartando requisições excedentes antes que os serviços sofressem crash por falta de memória.
3. **Vantagem do Cache:** O serviço de veterinários mostrou na prática o benefício do cache em microsserviços, não sofrendo impacto mesmo quando o resto do sistema estava saturado.
4. **Melhorias sugeridas:** Em um cenário de produção, seria necessário escalar horizontalmente o `customers-service` (mais instâncias com balanceador), usar um banco de dados externo otimizado e utilizar filas assíncronas (como RabbitMQ ou Kafka) para processar os cadastros em lote sem travar a API.

---

## Estrutura dos Arquivos

```
trabalho06-locust/
├── locustfile.py           # Cenários e perfis de teste do Locust
├── run_experiments.sh     # Script que roda as 60 execuções com checkpoint
├── analyze.py             # Script que processa os CSVs e gera gráficos
├── requirements.txt       # Dependências Python
├── README.md              # Documentação e análise dos resultados
└── results/
    ├── csv/               # Dados brutos dos 60 testes do Locust e CPU
    ├── tables/            # Tabelas resumo calculadas
    └── charts/            # Gráficos gerados
```
