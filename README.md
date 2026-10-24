# Trabalho Prático 06 — Avaliação de Desempenho de Microsserviços com Locust

Este repositório contém a implementação, automação e análise de desempenho da aplicação **Spring PetClinic Microservices** submetida a diferentes perfis de carga e intensidades de tráfego utilizando a ferramenta **Locust**.

---

## 📹 Vídeo Demonstrativo
> **Link do Vídeo (YouTube - 4 a 6 minutos):**  
> *[INSERIR O LINK DO VÍDEO AQUI]*  
> *(O vídeo demonstra: inicialização dos containers, execução do Locust em headless e interface web, monitoramento de CPU/memória com docker stats e interpretação dos gráficos/resultados obtidos).*

---

## 💻 Descrição do Ambiente Experimental

Os testes foram executados localmente no seguinte ambiente computacional:

| Componente | Especificação |
|---|---|
| **Sistema Operacional** | Ubuntu 24.04.5 LTS (Noble Numbat) - Kernel Linux 7.0.0-38-generic x86_64 |
| **Processador (CPU)** | 12th Gen Intel(R) Core(TM) i5-1235U (10 núcleos: 2 Performance + 8 Efficient, 12 threads) |
| **Memória RAM** | 16 GB (15 GiB utilizáveis) |
| **Docker Engine** | Versão 29.9.1 (build dfc520d) |
| **Docker Compose** | Versão v5.6.0 |
| **Python** | Versão 3.12.3 |
| **Locust** | Versão 2.47.0 |

---

## 🏗️ Arquitetura da Aplicação e Endpoints

A aplicação avaliada é o [Spring PetClinic Microservices](https://github.com/spring-petclinic/spring-petclinic-microservices), composta pelos seguintes microsserviços principais orquestrados via Docker Compose:
- **api-gateway** (Porta 8080): Ponto único de entrada, roteamento reativo e circuit breakers.
- **customers-service** (Porta 8081): Gerenciamento de proprietários (owners) e animais (pets).
- **vets-service** (Porta 8083): Gerenciamento de veterinários e especialidades.
- **visits-service** (Porta 8082): Gerenciamento de consultas e agendamentos.
- **discovery-server** (Eureka - Porta 8761): Service registry para descoberta dinâmica.
- **config-server** (Porta 8888): Servidor centralizado de configurações.

### Endpoints Avaliados:
Todas as requisições do teste são direcionadas ao **API Gateway** (`http://localhost:8080`), que reescreve os caminhos (`StripPrefix=2`) para os respectivos serviços de domínio:
- `GET /api/customer/owners` $\rightarrow$ Lista todos os proprietários (`customers-service`).
- `GET /api/customer/owners/{id}` $\rightarrow$ Consulta proprietário por ID (`customers-service`).
- `GET /api/vet/vets` $\rightarrow$ Lista os veterinários cadastrados (`vets-service`).
- `POST /api/customer/owners` $\rightarrow$ Cadastra um novo proprietário (`customers-service`).

---

## 🎯 Metodologia Experimental

### 1. Perfis de Carga
Foram implementados dois perfis de comportamento de usuário no [`locustfile.py`](locustfile.py):

| Operação | Perfil 1 — Leitura | Perfil 2 — Escrita |
|---|:---:|:---:|
| `GET /owners` | **45%** | **20%** |
| `GET /owners/{id}` | **35%** | **20%** |
| `GET /vets` | **15%** | **20%** |
| `POST /owners` | **5%** | **40%** |

- **Tempo de espera entre requisições (wait_time):** Intervalo aleatório uniforme entre 1 e 3 segundos (`between(1, 3)`), simulando o comportamento de usuários reais ("think time").

### 2. Cenários de Teste e Repetições
Os dois perfis foram submetidos a três cenários de intensidade de carga:

| Cenário | Usuários Simultâneos | Spawn Rate | Duração Total | Aquecimento (Warm-up) | Medição Efetiva |
|---|:---:|:---:|:---:|:---:|:---:|
| **A — Leve** | 30 | 10 usuários/s | 7 min (420s) | 1 min (60s) | 6 min (360s) |
| **B — Moderado** | 80 | 10 usuários/s | 7 min (420s) | 1 min (60s) | 6 min (360s) |
| **C — Elevado** | 150 | 10 usuários/s | 7 min (420s) | 1 min (60s) | 6 min (360s) |

- **Repetições:** 10 repetições por configuração.
- **Total de Execuções:** 2 perfis $\times$ 3 cenários $\times$ 10 repetições = **60 execuções**.
- **Descarte de Aquecimento:** O primeiro minuto de cada rodada é descartado pelo script de processamento estatístico ([`analyze.py`](analyze.py)), computando-se a média e o desvio padrão exclusivamente da janela estável de 6 minutos.
- **Mecanismo de Checkpoint & Resiliência:** O script de automação ([`run_experiments.sh`](run_experiments.sh)) salva cada resultado individualmente e valida se já existem CSVs concluídos, permitindo pausar e continuar os experimentos sem perda de dados. Durante cada teste, métricas de consumo de CPU e memória são registradas a cada 5 segundos via `docker stats`.

---

## 🚀 Instruções de Reprodução

### Pré-requisitos
- Docker Engine e Docker Compose instalados.
- Python 3.10+ com as dependências instaladas:
  ```bash
  pip install -r requirements.txt
  ```

### 1. Inicializar a Aplicação PetClinic
```bash
# Na pasta do repositório spring-petclinic-microservices:
cd ../spring-petclinic-microservices
docker compose up -d

# Aguarde cerca de 2 a 3 minutos para que todos os serviços se registrem no Eureka:
docker compose ps
```

Verifique se a aplicação está respondendo:
```bash
curl -I http://localhost:8080/api/customer/owners
# Deve retornar HTTP 200 OK
```

### 2. Executar os Experimentos
```bash
# Retorne à pasta do trabalho:
cd ../trabalho06-locust

# Executar a bateria automatizada de testes (com checkpoint e monitoramento de CPU):
chmod +x run_experiments.sh
./run_experiments.sh
```

### 3. Processar Resultados e Gerar Gráficos
Após a conclusão dos testes (ou de parte deles):
```bash
python3 analyze.py
```
Isso gerará os arquivos consolidados em:
- `results/tables/`: Tabelas resumo em CSV (`summary_all.csv`, `raw_all_repetitions.csv`).
- `results/charts/`: Gráficos comparativos de alta resolução em PNG.
- `results/tables/analise_questoes.txt`: Rascunho com o cálculo das respostas para as perguntas.

---

## 📊 Resultados e Análise

Os 60 testes foram executados com sucesso (10 repetições para cada um dos 6 cenários combinados). O primeiro minuto de cada rodada (warm-up) foi descartado pelo script [`analyze.py`](analyze.py) e os dados abaixo refletem a média e o comportamento estatístico da janela estável.

### Tabela Resumo Consolidada (Média das 10 repetições)

| Perfil | Cenário | Usuários | Tempo Médio (ms) | P95 (ms) | Vazão (req/s) | Total Requisições | Taxa de Falhas (%) | Desvio Padrão (ms) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Perfil 1 — Leitura** | A — Leve | 30 | **57.3** | **212.8** | **14.50** | 5.219 | **0.01%** | 56.0 |
| **Perfil 1 — Leitura** | B — Moderado | 80 | **1788.8** | **4513.9** | **25.74** | 9.265 | **68.98%** | 1993.3 |
| **Perfil 1 — Leitura** | C — Elevado | 150 | **659.9** | **2642.0** | **59.27** | 21.336 | **75.68%** | 639.1 |
| **Perfil 2 — Escrita** | A — Leve | 30 | **999.7** | **4011.5** | **10.81** | 3.890 | **75.59%** | 1011.3 |
| **Perfil 2 — Escrita** | B — Moderado | 80 | **317.0** | **1568.0** | **35.29** | 12.705 | **97.97%** | 72.5 |
| **Perfil 2 — Escrita** | C — Elevado | 150 | **77.2** | **215.9** | **73.02** | 26.287 | **99.77%** | 76.9 |

---

### Gráficos Comparativos

1. **Tempo de Resposta Médio por Usuários:**  
   ![Tempo de Resposta](results/charts/01_response_time_by_users.png)

2. **Percentil 95 (P95) por Usuários:**  
   ![P95](results/charts/02_p95_by_users.png)

3. **Comparativo de Vazão (Throughput):**  
   ![Vazão](results/charts/03_throughput_comparison.png)

4. **Taxa de Falhas por Cenário:**  
   ![Falhas](results/charts/04_failure_rate.png)

5. **Curva de Degradação do Tempo de Resposta:**  
   ![Evolução](results/charts/05_response_time_progression.png)

6. **Degradação por Operação / Endpoint:**  
   ![Degradação Endpoints](results/charts/06_endpoint_degradation.png)

7. **Consumo de CPU dos Microsserviços:**  
   ![Consumo CPU](results/charts/07_cpu_usage.png)

---

## ❓ Respostas às Questões de Análise

### 1. Como o aumento de usuários afeta o tempo de resposta?
* **No Perfil 1 (Leitura):** O aumento de 30 para 80 usuários gerou um impacto severo, elevando o tempo médio de resposta de **57.3 ms** para **1.788,8 ms** (um aumento de **31,2 vezes**), e o P95 saltou de 212.8 ms para 4.513,9 ms. No cenário de 150 usuários, o tempo aparente cai para **659.9 ms**, não por ganho de eficiência, mas pela atuação do **Circuit Breaker** do API Gateway, que passa a rejeitar rapidamente (*fail-fast* com tempo inferior a 10 ms) as requisições excedentes.
* **No Perfil 2 (Escrita):** Devido à alta contenção de escrita no banco de dados e bloqueios transacionais do `customers-service`, o tempo médio já iniciou elevado no cenário Leve (**999.7 ms** com 75.59% de falhas). Nos cenários moderado e elevado, o saturation point é atingido de imediato, abrindo o circuito e gerando rejeições quase instantâneas (tempo médio aparente de **77.2 ms** com 99.77% de falhas).

### 2. Qual perfil apresenta maior vazão?
* A vazão bruta média foi de **33.17 req/s** no Perfil 1 (Leitura) e de **39.71 req/s** no Perfil 2 (Escrita).
* **Entretanto, deve-se distinguir vazão bruta de vazão útil (goodput):** no Perfil 2 (Escrita), a vazão foi composta quase que exclusivamente por **respostas de erro imediatas (Circuit Breaker / HTTP 503)**, atingindo 73.02 req/s com 99.77% de falha no cenário C. Portanto, **em termos de requisições úteis concluídas com sucesso (goodput), o Perfil 1 (Leitura) apresentou desempenho amplamente superior**, processando com sucesso milhares de consultas no cenário leve e moderado.

### 3. Quais operações apresentam maior degradação?
Comparando o cenário Leve (30 usuários) com o Elevado (150 usuários), o fator de degradação do P95 por endpoint foi:
1. `GET /api/customer/owners/{id}`: **14.42× de degradação**
2. `POST /api/customer/owners`: **12.61× de degradação**
3. `GET /api/customer/owners`: **12.20× de degradação**
4. `GET /api/vet/vets`: **0.67× de degradação** (não sofreu degradação perceptível)

**Explicação arquitetural:** Os três endpoints de clientes pertencem ao `customers-service`, que sofreu gargalo direto de concorrência com o banco HSQLDB/MySQL. Já o endpoint `/api/vet/vets` é servido pelo `vets-service`, que utiliza **cache em memória** (`@Cacheable("vets")`) e não concorre com as tabelas de proprietários, demonstrando isolamento de falhas característico de uma boa arquitetura de microsserviços.

### 4. Como o consumo de CPU varia entre os cenários?
* **customers-service:** Foi o principal gargalo do sistema. Seu consumo de CPU médio variou de **182.0%** no cenário Leve para um pico de **208.6%** no cenário Moderado (saturando múltiplos núcleos de processamento devido ao parsing JSON, mapeamento ORM/Hibernate e persistência). No cenário Elevado, a CPU estabilizou em **109.3%**, pois as requisições estavam sendo bloqueadas antes no Gateway via circuit breaker.
* **api-gateway:** O consumo cresceu proporcionalmente ao volume de pacotes de rede e roteamento: **3.5%** no Leve, **6.1%** no Moderado e atingindo **15.4%** no Elevado.
* **vets-service:** Manteve consumo residual inferior a **1%** em todos os cenários (**0.4% a 0.9%**), protegido pelo cache local.

### 5. Qual cenário apresenta maior taxa de falhas?
* **O Cenário C — Elevado (150 usuários)** apresentou a maior taxa global de falhas, com média de **87.72%** (75.68% no Perfil de Leitura e **99.77%** no Perfil de Escrita).
* O Cenário B (80 usuários) registrou média de **83.47%** de falhas, e o Cenário A (30 usuários) registrou **37.80%** de falhas.
* O principal mecanismo causador das falhas sob sobrecarga foi o acionamento do **Circuit Breaker** e o timeout de conexão do pool de banco de dados do microsserviço de clientes.

---

## 🏁 Conclusões
1. **Ponto Único de Saturação:** O microsserviço `customers-service` é o principal gargalo da aplicação, com alto custo computacional em operações de escrita (`POST /owners`) e concorrência no banco de dados.
2. **Resiliência do API Gateway:** O Spring Cloud Gateway com Circuit Breaker comportou-se de forma esperada sob tempestade de requisições, evitando o travamento completo da máquina física ao rejeitar preventivamente requisições que levariam os microsserviços a *OutOfMemory* ou travamento permanente.
3. **Eficácia de Cache:** O `vets-service` exemplificou o benefício do isolamento e do uso de cache distribuído/local em microsserviços, permanecendo com latência mínima e consumo de CPU desprezível mesmo quando outros nós do sistema estavam em sobrecarga.
4. **Recomendações:** Para suportar a carga de 80 a 150 usuários simultâneos, recomenda-se:
   - Escalabilidade horizontal do `customers-service` com mais réplicas e balanceamento de carga.
   - Substituição do banco de dados embutido por um cluster dedicado (ex: PostgreSQL com pool HikariCP otimizado).
   - Otimização do pool de conexões e filas assíncronas (ex: mensageria com RabbitMQ ou Kafka) para o fluxo de escrita.

---

## 📁 Estrutura do Repositório

```
trabalho06-locust/
├── locustfile.py           # Definição dos perfis de carga e tarefas do Locust
├── run_experiments.sh     # Script de automação das 60 baterias com checkpoint
├── analyze.py             # Script de tratamento estatístico e geração de gráficos
├── requirements.txt       # Dependências Python (Locust, Pandas, Matplotlib, Numpy)
├── README.md              # Documentação completa, instruções e análise
└── results/
    ├── csv/               # Histórico e sumários de todas as 60 execuções do Locust e CPU
    ├── tables/            # Tabelas consolidadas em formato CSV e texto
    └── charts/            # Gráficos de desempenho gerados em PNG
```
