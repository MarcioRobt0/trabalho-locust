#!/usr/bin/env python3
"""
Trabalho 06 — Análise dos resultados dos experimentos Locust
Spring PetClinic Microservices

Processa os CSVs gerados pelo Locust, descarta o período de aquecimento (1 min),
calcula médias das 10 repetições e gera tabelas e gráficos comparativos.

Uso:
    python3 analyze.py

Saída:
    results/tables/  → CSVs com tabelas de resultados
    results/charts/  → Gráficos PNG comparativos
"""

import os
import glob
import sys
import warnings
import matplotlib
matplotlib.use("Agg")  # backend não-interativo (sem display)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

warnings.filterwarnings("ignore")

# =============================================================================
# Configuração
# =============================================================================
RESULTS_DIR   = Path("results/csv")
TABLES_DIR    = Path("results/tables")
CHARTS_DIR    = Path("results/charts")

WARMUP_SEC    = 60    # 1 minuto de aquecimento a descartar
MEASURE_SEC   = 360   # 6 minutos de medição efetiva
REPETITIONS   = 10

PROFILES = {
    "ReadProfile":  "Perfil 1 — Leitura",
    "WriteProfile": "Perfil 2 — Escrita",
}
SCENARIOS = {
    "A_leve":      30,
    "B_moderado":  80,
    "C_elevado":   150,
}
SCENARIO_LABELS = {
    "A_leve":     "A — Leve (30)",
    "B_moderado": "B — Moderado (80)",
    "C_elevado":  "C — Elevado (150)",
}
ENDPOINTS = [
    "GET /api/customer/owners",
    "GET /api/customer/owners/{id}",
    "GET /api/vet/vets",
    "POST /api/customer/owners",
]

TABLES_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

PALETTE = {
    "ReadProfile":  "#2196F3",   # azul
    "WriteProfile": "#F44336",   # vermelho
}
SCENARIO_COLORS = {
    "A_leve":     "#4CAF50",
    "B_moderado": "#FF9800",
    "C_elevado":  "#F44336",
}

plt.rcParams.update({
    "figure.dpi":       150,
    "font.size":        11,
    "axes.titlesize":   13,
    "axes.labelsize":   11,
    "legend.fontsize":  10,
    "xtick.labelsize":  10,
    "ytick.labelsize":  10,
})


# =============================================================================
# 1. Carregamento e filtragem dos CSVs
# =============================================================================

def load_history(profile: str, scenario: str, rep: int) -> pd.DataFrame | None:
    """Carrega o _stats_history.csv de uma execução e descarta o warmup."""
    path = RESULTS_DIR / f"{profile}_{scenario}_rep{rep}_stats_history.csv"
    if not path.exists():
        return None

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    # Filtra apenas linha "Aggregated" (total geral)
    df = df[df["Name"] == "Aggregated"].copy()
    if df.empty:
        return None

    # Descarta warmup: primeiros WARMUP_SEC segundos
    t_start = df["Timestamp"].min()
    df = df[df["Timestamp"] >= t_start + WARMUP_SEC].copy()
    return df


def load_per_endpoint_history(profile: str, scenario: str, rep: int) -> pd.DataFrame | None:
    """Carrega histórico por endpoint (para análise de degradação por operação)."""
    path = RESULTS_DIR / f"{profile}_{scenario}_rep{rep}_stats_history.csv"
    if not path.exists():
        return None

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    # Remove linha "Aggregated"
    df = df[df["Name"] != "Aggregated"].copy()
    if df.empty:
        return None

    t_start = df["Timestamp"].min()
    df = df[df["Timestamp"] >= t_start + WARMUP_SEC].copy()
    return df


def _get_col(df: pd.DataFrame, candidates: list) -> str | None:
    """Retorna o primeiro nome de coluna encontrado entre os candidatos."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def extract_metrics(df: pd.DataFrame) -> dict:
    """Extrai métricas de um DataFrame de histórico já filtrado."""
    if df is None or df.empty:
        return {}

    # Suporte a diferentes versões do Locust (nomes de colunas variam)
    col_p50 = _get_col(df, ["50%ile (ms)", "50%", "Total Median Response Time"])
    col_p95 = _get_col(df, ["95%ile (ms)", "95%"])
    col_avg = _get_col(df, ["Total Average Response Time"])

    rps  = df["Requests/s"].mean()
    fps  = df["Failures/s"].mean()
    p50  = df[col_p50].mean() if col_p50 else 0
    p95  = df[col_p95].mean() if col_p95 else 0
    avg  = df[col_avg].mean() if col_avg else p50   # fallback para mediana
    fail = (fps / rps * 100) if rps > 0 else 0
    total = rps * MEASURE_SEC

    return {
        "avg_response_ms":  avg,
        "p50_ms":           p50,
        "p95_ms":           p95,
        "throughput_rps":   rps,
        "total_requests":   total,
        "failure_rate_pct": fail,
    }


# =============================================================================
# 2. Coleta de métricas de todas as execuções
# =============================================================================

def collect_all_metrics() -> pd.DataFrame:
    """Agrega métricas de todas as execuções em um DataFrame."""
    rows = []
    missing = []

    for profile in PROFILES:
        for scenario in SCENARIOS:
            for rep in range(1, REPETITIONS + 1):
                df = load_history(profile, scenario, rep)
                if df is None:
                    missing.append(f"{profile}/{scenario}/rep{rep}")
                    continue
                metrics = extract_metrics(df)
                if not metrics:
                    missing.append(f"{profile}/{scenario}/rep{rep}")
                    continue
                rows.append({
                    "profile":  profile,
                    "scenario": scenario,
                    "rep":      rep,
                    **metrics,
                })

    if missing:
        print(f"⚠️  {len(missing)} execuções ausentes: {missing[:5]}{'...' if len(missing) > 5 else ''}")

    if not rows:
        print("❌ Nenhum resultado encontrado em results/csv/. Execute run_experiments.sh primeiro.")
        sys.exit(1)

    return pd.DataFrame(rows)


def average_repetitions(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a média das 10 repetições por (perfil, cenário)."""
    metrics_cols = ["avg_response_ms", "p95_ms", "throughput_rps", "total_requests", "failure_rate_pct"]
    return (
        df.groupby(["profile", "scenario"])[metrics_cols]
        .agg(["mean", "std"])
        .round(2)
    )


# =============================================================================
# 3. CPU dos containers
# =============================================================================

def load_cpu_data() -> pd.DataFrame | None:
    """Carrega dados de CPU coletados durante os experimentos."""
    consolidated_file = RESULTS_DIR / "docker_stats_consolidated.csv"
    if consolidated_file.exists():
        df = pd.read_csv(consolidated_file)
        df.columns = df.columns.str.strip()
        if not df.empty:
            return df

    cpu_files = list(RESULTS_DIR.glob("docker_stats_*.csv"))
    if not cpu_files:
        return None

    frames = []
    for f in cpu_files:
        if f.name == "docker_stats_consolidated.csv":
            continue
        parts = f.stem.replace("docker_stats_", "").split("_")
        if len(parts) < 3:
            continue
        try:
            df = pd.read_csv(f)
            df.columns = df.columns.str.strip()
            if not df.empty:
                frames.append(df)
        except Exception:
            continue

    if not frames:
        return None

    return pd.concat(frames, ignore_index=True)


# =============================================================================
# 4. Tabelas
# =============================================================================

def build_summary_table(avg_df: pd.DataFrame, raw_df: pd.DataFrame) -> pd.DataFrame:
    """Monta tabela resumo por perfil × cenário."""
    rows = []
    for profile in PROFILES:
        for scenario in SCENARIOS:
            subset = raw_df[(raw_df["profile"] == profile) & (raw_df["scenario"] == scenario)]
            if subset.empty:
                continue
            rows.append({
                "Perfil":               PROFILES[profile],
                "Cenário":              SCENARIO_LABELS[scenario],
                "Usuários":             SCENARIOS[scenario],
                "Tempo Médio (ms)":     round(subset["avg_response_ms"].mean(), 1),
                "P95 (ms)":             round(subset["p95_ms"].mean(), 1),
                "Vazão (req/s)":        round(subset["throughput_rps"].mean(), 2),
                "Total Requisições":    round(subset["total_requests"].mean()),
                "Taxa de Falhas (%)":   round(subset["failure_rate_pct"].mean(), 2),
                "Std Tempo Médio (ms)": round(subset["avg_response_ms"].std(), 1),
            })

    return pd.DataFrame(rows)


def save_tables(raw_df: pd.DataFrame, avg_df: pd.DataFrame):
    """Salva tabelas CSV e exibe resumo no terminal."""
    summary = build_summary_table(avg_df, raw_df)

    # Tabela completa
    out_path = TABLES_DIR / "summary_all.csv"
    summary.to_csv(out_path, index=False)
    print(f"\n📋 Tabela resumo salva: {out_path}")
    print(summary.to_string(index=False))

    # Tabela por perfil
    for profile, label in PROFILES.items():
        sub = summary[summary["Perfil"] == label]
        p_path = TABLES_DIR / f"summary_{profile}.csv"
        sub.to_csv(p_path, index=False)

    # Dados brutos (todas as repetições)
    raw_path = TABLES_DIR / "raw_all_repetitions.csv"
    raw_df.to_csv(raw_path, index=False)
    print(f"📋 Dados brutos salvos: {raw_path}")


# =============================================================================
# 5. Gráficos
# =============================================================================

def _save(fig: plt.Figure, name: str):
    path = CHARTS_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"📊 Gráfico salvo: {path}")


def chart_response_time_by_users(raw_df: pd.DataFrame):
    """Tempo de resposta vs. Número de usuários, por perfil."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)
    fig.suptitle("Tempo de Resposta × Usuários", fontsize=14, fontweight="bold")

    for ax, (profile, label) in zip(axes, PROFILES.items()):
        sub = raw_df[raw_df["profile"] == profile]
        grouped = sub.groupby("scenario")["avg_response_ms"]

        means = [grouped.get_group(s).mean() for s in SCENARIOS if s in sub["scenario"].values]
        stds  = [grouped.get_group(s).std()  for s in SCENARIOS if s in sub["scenario"].values]
        users = [SCENARIOS[s] for s in SCENARIOS if s in sub["scenario"].values]
        labels = [SCENARIO_LABELS[s] for s in SCENARIOS if s in sub["scenario"].values]

        ax.bar(labels, means, yerr=stds, color=PALETTE[profile],
               alpha=0.8, capsize=5, edgecolor="white")
        ax.set_title(label)
        ax.set_xlabel("Cenário (usuários)")
        ax.set_ylabel("Tempo Médio de Resposta (ms)")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}"))
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    _save(fig, "01_response_time_by_users")


def chart_p95_by_users(raw_df: pd.DataFrame):
    """P95 vs. Número de usuários, por perfil."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)
    fig.suptitle("Tempo P95 × Usuários", fontsize=14, fontweight="bold")

    for ax, (profile, label) in zip(axes, PROFILES.items()):
        sub = raw_df[raw_df["profile"] == profile]
        grouped = sub.groupby("scenario")["p95_ms"]

        means  = [grouped.get_group(s).mean() for s in SCENARIOS if s in sub["scenario"].values]
        stds   = [grouped.get_group(s).std()  for s in SCENARIOS if s in sub["scenario"].values]
        labels = [SCENARIO_LABELS[s] for s in SCENARIOS if s in sub["scenario"].values]

        ax.bar(labels, means, yerr=stds, color=PALETTE[profile],
               alpha=0.8, capsize=5, edgecolor="white")
        ax.set_title(label)
        ax.set_xlabel("Cenário (usuários)")
        ax.set_ylabel("P95 (ms)")
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    _save(fig, "02_p95_by_users")


def chart_throughput_comparison(raw_df: pd.DataFrame):
    """Vazão comparativa entre perfis por cenário."""
    scenarios = list(SCENARIOS.keys())
    x = np.arange(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Vazão (req/s) — Comparação entre Perfis", fontsize=14, fontweight="bold")

    for i, (profile, label) in enumerate(PROFILES.items()):
        sub = raw_df[raw_df["profile"] == profile]
        means = [sub[sub["scenario"] == s]["throughput_rps"].mean() for s in scenarios]
        stds  = [sub[sub["scenario"] == s]["throughput_rps"].std()  for s in scenarios]
        offset = (i - 0.5) * width
        ax.bar(x + offset, means, width, label=label,
               color=PALETTE[profile], alpha=0.85, capsize=5,
               yerr=stds, edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in scenarios])
    ax.set_ylabel("Vazão (req/s)")
    ax.set_xlabel("Cenário (usuários)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _save(fig, "03_throughput_comparison")


def chart_failure_rate(raw_df: pd.DataFrame):
    """Taxa de falhas por cenário e perfil."""
    scenarios = list(SCENARIOS.keys())
    x = np.arange(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Taxa de Falhas (%) por Cenário", fontsize=14, fontweight="bold")

    for i, (profile, label) in enumerate(PROFILES.items()):
        sub = raw_df[raw_df["profile"] == profile]
        means = [sub[sub["scenario"] == s]["failure_rate_pct"].mean() for s in scenarios]
        stds  = [sub[sub["scenario"] == s]["failure_rate_pct"].std()  for s in scenarios]
        offset = (i - 0.5) * width
        bars = ax.bar(x + offset, means, width, label=label,
                      color=PALETTE[profile], alpha=0.85, capsize=5,
                      yerr=stds, edgecolor="white")
        for bar, val in zip(bars, means):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                        f"{val:.1f}%", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in scenarios])
    ax.set_ylabel("Taxa de Falhas (%)")
    ax.set_xlabel("Cenário (usuários)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _save(fig, "04_failure_rate")


def chart_response_time_progression(raw_df: pd.DataFrame):
    """Evolução do tempo médio conforme aumento de usuários (linha)."""
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Evolução do Tempo de Resposta com Aumento de Carga", fontsize=14, fontweight="bold")

    scenarios_order = list(SCENARIOS.keys())
    x = [SCENARIOS[s] for s in scenarios_order]

    for profile, label in PROFILES.items():
        sub = raw_df[raw_df["profile"] == profile]
        means = [sub[sub["scenario"] == s]["avg_response_ms"].mean() for s in scenarios_order]
        stds  = [sub[sub["scenario"] == s]["avg_response_ms"].std()  for s in scenarios_order]

        ax.plot(x, means, "o-", label=label, color=PALETTE[profile], linewidth=2, markersize=7)
        ax.fill_between(x,
                        [m - s for m, s in zip(means, stds)],
                        [m + s for m, s in zip(means, stds)],
                        color=PALETTE[profile], alpha=0.15)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{u} usuários" for u in x])
    ax.set_ylabel("Tempo Médio de Resposta (ms)")
    ax.set_xlabel("Carga (usuários simultâneos)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save(fig, "05_response_time_progression")


def chart_endpoint_degradation(raw_df: pd.DataFrame):
    """Degradação por endpoint (operação) entre cenário leve e elevado."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle("Degradação por Operação (Leve → Elevado)", fontsize=14, fontweight="bold")

    for ax, (profile, label) in zip(axes, PROFILES.items()):
        all_data = {}
        for scenario in ["A_leve", "C_elevado"]:
            rows = []
            for rep in range(1, REPETITIONS + 1):
                df_ep = load_per_endpoint_history(profile, scenario, rep)
                if df_ep is None:
                    continue
                for ep_name in df_ep["Name"].unique():
                    ep_df = df_ep[df_ep["Name"] == ep_name]
                    col_p95 = _get_col(ep_df, ["95%ile (ms)", "95%"])
                    rows.append({
                        "endpoint": ep_name,
                        "p95":      ep_df[col_p95].mean() if col_p95 else 0,
                        "rep":      rep,
                    })
            if rows:
                all_data[scenario] = pd.DataFrame(rows).groupby("endpoint")["p95"].mean()

        if "A_leve" not in all_data or "C_elevado" not in all_data:
            ax.text(0.5, 0.5, "Dados insuficientes", ha="center", va="center",
                    transform=ax.transAxes)
            ax.set_title(label)
            continue

        endpoints = list(all_data["A_leve"].index)
        x = np.arange(len(endpoints))
        w = 0.35

        ax.bar(x - w/2, [all_data["A_leve"].get(e, 0) for e in endpoints],
               w, label="A — Leve (30)", color=SCENARIO_COLORS["A_leve"], alpha=0.85)
        ax.bar(x + w/2, [all_data["C_elevado"].get(e, 0) for e in endpoints],
               w, label="C — Elevado (150)", color=SCENARIO_COLORS["C_elevado"], alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels(endpoints, rotation=20, ha="right")
        ax.set_ylabel("P95 (ms)")
        ax.set_title(label)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    _save(fig, "06_endpoint_degradation")


def chart_cpu_usage(cpu_df: pd.DataFrame):
    """Utilização de CPU por serviço e cenário."""
    if cpu_df is None or cpu_df.empty:
        print("⚠️  Dados de CPU não encontrados — pulando gráfico de CPU.")
        return

    cpu_col = [c for c in cpu_df.columns if "cpu" in c.lower() or "CPU" in c]
    name_col = [c for c in cpu_df.columns if "name" in c.lower() or "Name" in c]

    if not cpu_col or not name_col:
        print("⚠️  Colunas de CPU não identificadas no arquivo.")
        return

    cpu_col  = cpu_col[0]
    name_col = name_col[0]

    # Garante conversão para float
    cpu_df[cpu_col] = cpu_df[cpu_col].astype(str).str.replace("%", "").astype(float)

    services = [s for s in ["customers-service", "api-gateway", "vets-service", "visits-service"] if s in cpu_df[name_col].values]
    if not services:
        services = list(cpu_df[name_col].unique()[:4])

    scenarios = list(SCENARIOS.keys())

    fig, axes = plt.subplots(1, len(PROFILES), figsize=(16, 6), sharey=True)
    fig.suptitle("Utilização Média de CPU (%) por Microsserviço e Cenário", fontsize=14, fontweight="bold")

    for ax, (profile, label) in zip(axes, PROFILES.items()):
        sub = cpu_df[cpu_df["profile"] == profile]
        x = np.arange(len(scenarios))
        w = 0.8 / len(services)

        for i, svc in enumerate(services):
            svc_sub = sub[sub[name_col] == svc]
            means = [svc_sub[svc_sub["scenario"] == s][cpu_col].mean() if not svc_sub[svc_sub["scenario"] == s].empty else 0 for s in scenarios]
            offset = (i - len(services) / 2 + 0.5) * w
            ax.bar(x + offset, means, w, label=svc, alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels([SCENARIO_LABELS[s] for s in scenarios])
        ax.set_ylabel("CPU (%)")
        ax.set_title(label)
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    _save(fig, "07_cpu_usage")


# =============================================================================
# 6. Respostas automáticas às questões de análise
# =============================================================================

def answer_questions(raw_df: pd.DataFrame, cpu_df: pd.DataFrame | None):
    """Gera respostas automáticas baseadas nos dados, para inclusão no README."""
    scenarios = list(SCENARIOS.keys())
    output = []

    output.append("\n" + "=" * 70)
    output.append("RESPOSTAS ÀS QUESTÕES DE ANÁLISE (baseadas nos dados coletados)")
    output.append("=" * 70)

    # Q1: Como o aumento de usuários afeta o tempo de resposta?
    output.append("\n1. Como o aumento de usuários afeta o tempo de resposta?")
    for profile, label in PROFILES.items():
        sub = raw_df[raw_df["profile"] == profile]
        vals = {s: sub[sub["scenario"] == s]["avg_response_ms"].mean() for s in scenarios}
        if all(v > 0 for v in vals.values()):
            delta = vals["C_elevado"] / vals["A_leve"]
            output.append(f"   [{label}] Leve={vals['A_leve']:.0f}ms → "
                          f"Moderado={vals['B_moderado']:.0f}ms → "
                          f"Elevado={vals['C_elevado']:.0f}ms "
                          f"(×{delta:.1f} de aumento)")

    # Q2: Qual perfil apresenta maior vazão?
    output.append("\n2. Qual perfil apresenta maior vazão?")
    for profile, label in PROFILES.items():
        sub = raw_df[raw_df["profile"] == profile]
        mean_rps = sub["throughput_rps"].mean()
        output.append(f"   [{label}] Vazão média: {mean_rps:.2f} req/s")

    max_profile = max(PROFILES, key=lambda p: raw_df[raw_df["profile"] == p]["throughput_rps"].mean())
    output.append(f"   → Maior vazão: {PROFILES[max_profile]}")

    # Q3: Quais operações apresentam maior degradação?
    output.append("\n3. Quais operações apresentam maior degradação?")
    degradations = {}
    for profile in PROFILES:
        for rep in range(1, REPETITIONS + 1):
            leve  = load_per_endpoint_history(profile, "A_leve",    rep)
            elev  = load_per_endpoint_history(profile, "C_elevado",  rep)
            if leve is None or elev is None:
                continue
            for ep in leve["Name"].unique():
                col_p95_l = _get_col(leve[leve["Name"] == ep], ["95%ile (ms)", "95%"])
                col_p95_e = _get_col(elev[elev["Name"] == ep], ["95%ile (ms)", "95%"]) if ep in elev["Name"].values else None
                p95_l = leve[leve["Name"] == ep][col_p95_l].mean() if col_p95_l else 0
                p95_e = elev[elev["Name"] == ep][col_p95_e].mean() if (col_p95_e and ep in elev["Name"].values) else 0
                if p95_l > 0 and ep not in degradations:
                    degradations[ep] = p95_e / p95_l

    if degradations:
        for ep, ratio in sorted(degradations.items(), key=lambda x: -x[1]):
            output.append(f"   {ep}: ×{ratio:.2f} de degradação")
    else:
        output.append("   (dados de endpoint não disponíveis ainda)")

    # Q4: Como o consumo de CPU varia entre os cenários?
    output.append("\n4. Como o consumo de CPU varia entre os cenários?")
    if cpu_df is not None and not cpu_df.empty:
        cpu_col = [c for c in cpu_df.columns if "cpu" in c.lower()][0]
        name_col = [c for c in cpu_df.columns if "name" in c.lower()][0]
        if cpu_df[cpu_col].dtype == object:
            cpu_df[cpu_col] = cpu_df[cpu_col].astype(str).str.replace("%", "").astype(float)
        for s in scenarios:
            sub_s = cpu_df[cpu_df["scenario"] == s]
            if not sub_s.empty:
                output.append(f"   [{SCENARIO_LABELS[s]}]")
                for svc in ["customers-service", "api-gateway", "vets-service"]:
                    sub_svc = sub_s[sub_s[name_col] == svc]
                    if not sub_svc.empty:
                        output.append(f"      - {svc}: {sub_svc[cpu_col].mean():.1f}%")
    else:
        output.append("   (dados de CPU não disponíveis — verifique results/csv/docker_stats_*.csv)")

    # Q5: Qual cenário apresenta maior taxa de falhas?
    output.append("\n5. Qual cenário apresenta maior taxa de falhas?")
    for s in scenarios:
        mean_fail = raw_df[raw_df["scenario"] == s]["failure_rate_pct"].mean()
        output.append(f"   {SCENARIO_LABELS[s]}: {mean_fail:.2f}%")
    max_scenario = max(scenarios, key=lambda s: raw_df[raw_df["scenario"] == s]["failure_rate_pct"].mean())
    output.append(f"   → Maior taxa de falhas: {SCENARIO_LABELS[max_scenario]}")

    output.append("\n" + "=" * 70)

    text = "\n".join(output)
    print(text)

    # Salva em arquivo para copiar no README
    answers_path = TABLES_DIR / "analise_questoes.txt"
    answers_path.write_text(text, encoding="utf-8")
    print(f"\n📄 Respostas salvas em: {answers_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print(" Trabalho 06 — Análise dos Resultados Locust")
    print("=" * 60)

    # 1. Carrega e agrega métricas
    print("\n🔄 Carregando CSVs...")
    raw_df = collect_all_metrics()
    avg_df = average_repetitions(raw_df)

    total_reps = len(raw_df)
    print(f"✅ {total_reps} execuções carregadas "
          f"({total_reps}/{len(PROFILES) * len(SCENARIOS) * REPETITIONS} esperadas)")

    # 2. Salva tabelas
    print("\n📋 Gerando tabelas...")
    save_tables(raw_df, avg_df)

    # 3. Gera gráficos
    print("\n📊 Gerando gráficos...")
    chart_response_time_by_users(raw_df)
    chart_p95_by_users(raw_df)
    chart_throughput_comparison(raw_df)
    chart_failure_rate(raw_df)
    chart_response_time_progression(raw_df)
    chart_endpoint_degradation(raw_df)

    # 4. CPU (opcional)
    cpu_df = load_cpu_data()
    chart_cpu_usage(cpu_df)

    # 5. Questões de análise
    print("\n❓ Gerando respostas às questões...")
    answer_questions(raw_df, cpu_df)

    print("\n✅ Análise concluída!")
    print(f"   Tabelas : results/tables/")
    print(f"   Gráficos: results/charts/")


if __name__ == "__main__":
    main()
