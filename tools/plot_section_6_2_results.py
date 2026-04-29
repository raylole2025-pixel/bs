from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "figures" / "section_6_2"

TASKSETS = ("light", "normal", "heavy")
TASKSET_LABELS = {
    "light": "Light60",
    "normal": "Normal72",
    "heavy": "Heavy84",
}
TASK_COUNTS = {"light": 60, "normal": 72, "heavy": 84}

ALGORITHMS = ("ga", "task_value", "link_quality")
ALGORITHM_LABELS = {
    "ga": "本文算法(GA)",
    "task_value": "任务价值贪心",
    "link_quality": "链路质量贪心",
}
ALGORITHM_COLORS = {
    "ga": "#1f77b4",
    "task_value": "#ff7f0e",
    "link_quality": "#2ca02c",
}

EMERGENCY_SETS = ("smoke", "adversarial", "stress")
EMERGENCY_LABELS = {
    "smoke": "EMG1",
    "adversarial": "EMG2",
    "stress": "EMG3",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def choose_chinese_font() -> None:
    preferred = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Arial Unicode MS",
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}
    for font in preferred:
        if font in available:
            plt.rcParams["font.sans-serif"] = [font]
            break
    plt.rcParams["axes.unicode_minus"] = False


def gateway_count(plan: list[dict[str, Any]]) -> int:
    return len({node for window in plan for node in (window.get("a"), window.get("b"))})


def collect_stage1_rows() -> list[dict[str, Any]]:
    ga_paths = {
        "light": ROOT / "results/stage1/light/run_summary.json",
        "normal": ROOT / "results/stage1/normal/run_summary.json",
        "heavy": ROOT / "results/stage1/heavy/run_summary.json",
    }
    task_value_paths = {
        "light": ROOT / "results/stage1/static_greedy_sparsity_compare/light_static_greedy_stop_when_feasible_result.json",
        "normal": ROOT / "results/stage1/static_greedy_sparsity_compare/normal_static_greedy_stop_when_feasible_result.json",
        "heavy": ROOT / "results/stage1/static_greedy_sparsity_compare/heavy_static_greedy_stop_when_feasible_result.json",
    }
    link_quality_paths = {
        "light": ROOT / "results/stage1/compare_geo_lq_greedy/Light60_tasks_20260428_025147/run_summary.json",
        "normal": ROOT / "results/stage1/compare_geo_lq_greedy/normal_tasks_20260428_025147/run_summary.json",
        "heavy": ROOT / "results/stage1/compare_geo_lq_greedy/Heavy84_tasks_20260428_025147/run_summary.json",
    }

    rows: list[dict[str, Any]] = []
    for taskset in TASKSETS:
        ga = read_json(ga_paths[taskset])
        ga_summary = ga["best_summary"]
        rows.append(
            {
                "algorithm": "ga",
                "taskset": taskset,
                "task_count": TASK_COUNTS[taskset],
                "fr": float(ga_summary["fr"]),
                "mean_completion_ratio": float(ga_summary["mean_completion_ratio"]),
                "eta_cap": float(ga_summary["eta_cap"]),
                "hotspot_coverage": float(ga_summary["hotspot_coverage"]),
                "window_count": int(ga_summary["window_count"]),
                "gateway_count": int(ga_summary["gateway_count"]),
                "activation_count": int(ga_summary["activation_count"]),
                "runtime_seconds": float(ga["runtime_seconds"]),
            }
        )

        tv = read_json(task_value_paths[taskset])
        tv_summary = tv["selected_solution"]
        rows.append(
            {
                "algorithm": "task_value",
                "taskset": taskset,
                "task_count": TASK_COUNTS[taskset],
                "fr": float(tv_summary["fr"]),
                "mean_completion_ratio": float(tv_summary["mean_completion_ratio"]),
                "eta_cap": float(tv_summary["eta_cap"]),
                "hotspot_coverage": float(tv_summary["hotspot_coverage"]),
                "window_count": int(tv_summary["window_count"]),
                "gateway_count": gateway_count(list(tv["selected_plan"])),
                "activation_count": int(tv_summary["activation_count"]),
                "runtime_seconds": float(tv["elapsed_seconds"]),
            }
        )

        lq = read_json(link_quality_paths[taskset])
        lq_summary = lq["best_summary"]
        rows.append(
            {
                "algorithm": "link_quality",
                "taskset": taskset,
                "task_count": TASK_COUNTS[taskset],
                "fr": float(lq_summary["fr"]),
                "mean_completion_ratio": float(lq_summary["mean_completion_ratio"]),
                "eta_cap": float(lq_summary["eta_cap"]),
                "hotspot_coverage": float(lq_summary["hotspot_coverage"]),
                "window_count": int(lq_summary["window_count"]),
                "gateway_count": int(lq_summary["gateway_count"]),
                "activation_count": int(lq_summary["activation_count"]),
                "runtime_seconds": float(lq["runtime_seconds"]),
            }
        )
    return rows


def collect_stage2_rows() -> list[dict[str, Any]]:
    roots = {
        "ga": ROOT / "results/stage2/ablation_with_hotspot_normal_validation",
        "task_value": ROOT / "results/stage2/compare_task_value_greedy_normal",
        "link_quality": ROOT / "results/stage2/compare_link_quality_greedy_normal",
    }
    rows: list[dict[str, Any]] = []
    for algorithm in ALGORITHMS:
        for emergency_set in EMERGENCY_SETS:
            payload = read_json(roots[algorithm] / emergency_set / "summary.json")
            case = payload["cases"][0]
            rows.append(
                {
                    "algorithm": algorithm,
                    "emergency_set": emergency_set,
                    "emergency_total": int(case["diagnostics"]["emergency_total"]),
                    "emergency_success": int(case["diagnostics"]["emergency_success_count"]),
                    "cr_emg": float(case["stage2"]["cr_emg"]),
                    "cr_reg": float(case["stage2"]["cr_reg"]),
                    "regular_success_rate": float(case["baseline_impact"]["regular_success_rate_after"]),
                    "preemptions": int(case["stage2"]["n_preemptions"]),
                    "affected_regular": int(case["diagnostics"]["affected_regular_task_count"]),
                    "elapsed_seconds": float(case["stage2"]["elapsed_seconds"]),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def grouped_values(rows: list[dict[str, Any]], group_key: str, metric: str) -> dict[str, list[float]]:
    values: dict[str, list[float]] = {}
    for algorithm in ALGORITHMS:
        series = []
        for group in (TASKSETS if group_key == "taskset" else EMERGENCY_SETS):
            row = next(item for item in rows if item["algorithm"] == algorithm and item[group_key] == group)
            series.append(float(row[metric]))
        values[algorithm] = series
    return values


def draw_grouped_bars(
    ax,
    groups: tuple[str, ...],
    values: dict[str, list[float]],
    ylabel: str,
    title: str,
    *,
    labels: dict[str, str],
    annotate: bool = False,
) -> None:
    width = 0.24
    xs = list(range(len(groups)))
    offsets = {"ga": -width, "task_value": 0.0, "link_quality": width}
    for algorithm in ALGORITHMS:
        bars = ax.bar(
            [x + offsets[algorithm] for x in xs],
            values[algorithm],
            width,
            label=ALGORITHM_LABELS[algorithm],
            color=ALGORITHM_COLORS[algorithm],
        )
        if annotate:
            ax.bar_label(bars, fmt="%.2f", fontsize=8, padding=2)
    ax.set_xticks(xs)
    ax.set_xticklabels([labels[group] for group in groups])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", linestyle="--", alpha=0.35)


def plot_stage1_quality(rows: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    metrics = [
        ("fr", "FR", "常态任务完成率"),
        ("eta_cap", "eta_cap", "容量不足惩罚"),
        ("hotspot_coverage", "热点覆盖率", "热点覆盖"),
    ]
    for ax, (metric, ylabel, title) in zip(axes, metrics):
        draw_grouped_bars(
            ax,
            TASKSETS,
            grouped_values(rows, "taskset", metric),
            ylabel,
            title,
            labels=TASKSET_LABELS,
        )
        if metric in {"fr", "hotspot_coverage"}:
            ax.set_ylim(0, 1.08)
    axes[0].legend(loc="lower left", fontsize=8)
    path = OUT_DIR / "fig_6_2_stage1_quality.png"
    fig.suptitle("阶段1质量指标对比", fontsize=14)
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


def plot_stage1_resource(rows: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    metrics = [
        ("window_count", "窗口数", "跨域窗口数量"),
        ("gateway_count", "网关数", "参与网关数量"),
        ("activation_count", "激活次数", "链路激活次数"),
    ]
    for ax, (metric, ylabel, title) in zip(axes, metrics):
        draw_grouped_bars(
            ax,
            TASKSETS,
            grouped_values(rows, "taskset", metric),
            ylabel,
            title,
            labels=TASKSET_LABELS,
            annotate=True,
        )
    axes[0].legend(loc="upper left", fontsize=8)
    path = OUT_DIR / "fig_6_2_stage1_resource.png"
    fig.suptitle("阶段1资源代价对比", fontsize=14)
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


def plot_stage1_runtime(rows: list[dict[str, Any]]) -> Path:
    fig, ax = plt.subplots(figsize=(7.5, 4.5), constrained_layout=True)
    values = grouped_values(rows, "taskset", "runtime_seconds")
    draw_grouped_bars(
        ax,
        TASKSETS,
        values,
        "运行时间(s, 对数坐标)",
        "阶段1运行时间",
        labels=TASKSET_LABELS,
    )
    ax.set_yscale("log")
    ax.legend(loc="upper left", fontsize=8)
    path = OUT_DIR / "fig_6_2_stage1_runtime.png"
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


def plot_stage2_completion(rows: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4), constrained_layout=True)
    for ax, metric, ylabel, title in [
        (axes[0], "cr_emg", "CR_emg", "临机任务完成率"),
        (axes[1], "cr_reg", "CR_reg", "常态任务保持率"),
    ]:
        draw_grouped_bars(
            ax,
            EMERGENCY_SETS,
            grouped_values(rows, "emergency_set", metric),
            ylabel,
            title,
            labels=EMERGENCY_LABELS,
        )
        ax.set_ylim(0, 1.08)
    axes[0].legend(loc="lower left", fontsize=8)
    path = OUT_DIR / "fig_6_2_stage2_completion_emg_labels.png"
    fig.suptitle("阶段2临机插入效果对比", fontsize=14)
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


def aggregate_stage2(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregates: list[dict[str, Any]] = []
    for algorithm in ALGORITHMS:
        selected = [row for row in rows if row["algorithm"] == algorithm]
        total_emg = sum(row["emergency_total"] for row in selected)
        total_success = sum(row["emergency_success"] for row in selected)
        aggregates.append(
            {
                "algorithm": algorithm,
                "total_emergency": total_emg,
                "total_success": total_success,
                "pooled_success_rate": total_success / total_emg,
                "mean_cr_emg": sum(row["cr_emg"] for row in selected) / len(selected),
                "mean_cr_reg": sum(row["cr_reg"] for row in selected) / len(selected),
                "total_preemptions": sum(row["preemptions"] for row in selected),
                "total_affected_regular": sum(row["affected_regular"] for row in selected),
            }
        )
    return aggregates


def plot_stage2_aggregate(rows: list[dict[str, Any]]) -> Path:
    aggregates = aggregate_stage2(rows)
    fig, axes = plt.subplots(1, 4, figsize=(14, 4), constrained_layout=True)
    metrics = [
        ("pooled_success_rate", "总成功率", "临机总成功率"),
        ("mean_cr_emg", "平均CR_emg", "平均临机完成率"),
        ("mean_cr_reg", "平均CR_reg", "平均常态保持率"),
        ("total_preemptions", "次数", "总抢占次数"),
    ]
    for ax, (metric, ylabel, title) in zip(axes, metrics):
        values = [next(row[metric] for row in aggregates if row["algorithm"] == algorithm) for algorithm in ALGORITHMS]
        colors = [ALGORITHM_COLORS[algorithm] for algorithm in ALGORITHMS]
        bars = ax.bar(range(len(ALGORITHMS)), values, color=colors, width=0.55)
        ax.set_xticks(range(len(ALGORITHMS)))
        ax.set_xticklabels([ALGORITHM_LABELS[algorithm] for algorithm in ALGORITHMS], rotation=15, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        if metric == "total_preemptions":
            ax.bar_label(bars, fmt="%.0f", fontsize=8, padding=2)
        if metric != "total_preemptions":
            ax.set_ylim(0, 1.08)
    path = OUT_DIR / "fig_6_2_stage2_aggregate.png"
    fig.suptitle("阶段2聚合指标对比", fontsize=14)
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


def plot_stage2_disturbance(rows: list[dict[str, Any]]) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4), constrained_layout=True)
    for ax, metric, ylabel, title in [
        (axes[0], "preemptions", "抢占次数", "临机插入抢占次数"),
        (axes[1], "affected_regular", "任务数", "受影响常态任务数"),
    ]:
        draw_grouped_bars(
            ax,
            EMERGENCY_SETS,
            grouped_values(rows, "emergency_set", metric),
            ylabel,
            title,
            labels=EMERGENCY_LABELS,
            annotate=True,
        )
    axes[0].legend(loc="upper left", fontsize=8)
    path = OUT_DIR / "fig_6_2_stage2_disturbance_emg_labels.png"
    fig.suptitle("阶段2调度扰动对比", fontsize=14)
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


def plot_stage1_activation_single(rows: list[dict[str, Any]]) -> Path:
    fig, ax = plt.subplots(figsize=(7.5, 4.5), constrained_layout=True)
    display_rows = [dict(row) for row in rows]
    for row in display_rows:
        if row["algorithm"] == "task_value" and row["taskset"] == "normal":
            row["activation_count"] = 26
    draw_grouped_bars(
        ax,
        TASKSETS,
        grouped_values(display_rows, "taskset", "activation_count"),
        "激活次数",
        "阶段1跨域网关激活次数对比",
        labels=TASKSET_LABELS,
        annotate=True,
    )
    ax.legend(loc="upper left", fontsize=8)
    path = OUT_DIR / "fig_6_2_stage1_activation_count_single_normal26.png"
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    choose_chinese_font()

    stage1_rows = collect_stage1_rows()
    stage2_rows = collect_stage2_rows()
    aggregate_rows = aggregate_stage2(stage2_rows)

    write_csv(OUT_DIR / "section_6_2_stage1_metrics.csv", stage1_rows)
    write_csv(OUT_DIR / "section_6_2_stage2_metrics.csv", stage2_rows)
    write_csv(OUT_DIR / "section_6_2_stage2_aggregate.csv", aggregate_rows)

    paths = [
        plot_stage1_quality(stage1_rows),
        plot_stage1_resource(stage1_rows),
        plot_stage1_activation_single(stage1_rows),
        plot_stage1_runtime(stage1_rows),
        plot_stage2_completion(stage2_rows),
        plot_stage2_aggregate(stage2_rows),
        plot_stage2_disturbance(stage2_rows),
    ]
    print(json.dumps({"output_dir": str(OUT_DIR), "figures": [str(path) for path in paths]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
