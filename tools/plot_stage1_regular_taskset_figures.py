from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results" / "stage1"
OUTPUT_DIR = RESULTS_ROOT / "figures"


@dataclass(frozen=True)
class GAMetrics:
    label: str
    task_count: int
    hotspot_coverage: float
    eta_cap: float
    activation_count: int
    window_count: int
    runtime_seconds: float
    generations: int
    fr: float
    completion_ratio: float


@dataclass(frozen=True)
class AlgorithmMetrics:
    label: str
    algorithm: str
    hotspot_coverage: float
    eta_cap: float
    activation_count: int
    window_count: int
    runtime_seconds: float
    fr: float
    completion_ratio: float


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _task_count(tasks_path: Path) -> int:
    data = _read_json(tasks_path)
    if isinstance(data, list):
        return len(data)
    for key in ("tasks", "regular_tasks"):
        items = data.get(key)
        if isinstance(items, list):
            return len(items)
    raise ValueError(f"Cannot infer task count from {tasks_path}")


def load_ga_metrics() -> list[GAMetrics]:
    specs = [
        ("Light", "Light60", RESULTS_ROOT / "light" / "Light60_stage1_result.json", RESULTS_ROOT / "light" / "Light60_tasks.json"),
        ("Normal", "Normal", RESULTS_ROOT / "normal" / "normal_stage1_result.json", RESULTS_ROOT / "normal" / "normal_tasks.json"),
        ("Heavy", "Heavy84", RESULTS_ROOT / "heavy" / "Heavy84_stage1_result.json", RESULTS_ROOT / "heavy" / "Heavy84_tasks.json"),
    ]
    rows: list[GAMetrics] = []
    for short_label, default_name, result_path, tasks_path in specs:
        data = _read_json(result_path)
        selected = data["selected_solution"]
        count = _task_count(tasks_path)
        label = f"{default_name if short_label != 'Normal' else f'Normal{count}'}"
        rows.append(
            GAMetrics(
                label=label,
                task_count=count,
                hotspot_coverage=float(selected["hotspot_coverage"]),
                eta_cap=float(selected["eta_cap"]),
                activation_count=int(selected["activation_count"]),
                window_count=int(selected["window_count"]),
                runtime_seconds=float(data.get("elapsed_seconds", data["runtime_seconds"])),
                generations=int(data.get("generations", 0)),
                fr=float(selected["fr"]),
                completion_ratio=float(selected["mean_completion_ratio"]),
            )
        )
    return rows


def load_comparison_metrics() -> list[AlgorithmMetrics]:
    comparison = _read_json(RESULTS_ROOT / "static_greedy_sparsity_compare" / "comparison_summary.json")
    order = [("light", "Light60"), ("normal", "Normal72"), ("heavy", "Heavy84")]
    rows: list[AlgorithmMetrics] = []
    for key, label in order:
        block = comparison[key]
        for algorithm_key, algorithm_name in (
            ("ga_existing", "GA"),
            ("static_greedy_stop_when_feasible", "Static greedy (stop when feasible)"),
        ):
            item = block[algorithm_key]
            rows.append(
                AlgorithmMetrics(
                    label=label,
                    algorithm=algorithm_name,
                    hotspot_coverage=float(item["hotspot_coverage"]),
                    eta_cap=float(item["eta_cap"]),
                    activation_count=int(item["activation_count"]),
                    window_count=int(item["window_count"]),
                    runtime_seconds=float(item["runtime_seconds"]),
                    fr=float(item["fr"]),
                    completion_ratio=float(item["mean_completion_ratio"]),
                )
            )
    return rows


def _apply_panel_style(ax: plt.Axes) -> None:
    ax.set_facecolor("#ffffff")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.8, alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#8a8a8a")
    ax.spines["bottom"].set_color("#8a8a8a")


def _annotate_bars(ax: plt.Axes, fmt: str = "{:.3f}", dy: float = 0.0) -> None:
    for patch in ax.patches:
        height = patch.get_height()
        if height is None:
            continue
        ax.text(
            patch.get_x() + patch.get_width() / 2.0,
            height + dy,
            fmt.format(height),
            ha="center",
            va="bottom",
            fontsize=9,
            color="#2f2a24",
        )


def _new_figure(figsize: tuple[float, float] = (8.8, 6.0)) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=figsize, facecolor="#ffffff")
    _apply_panel_style(ax)
    return fig, ax


def _save_figure(fig: plt.Figure, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)


def build_ga_single_figures(rows: list[GAMetrics]) -> list[Path]:
    labels = [row.label for row in rows]
    x = np.arange(len(rows))
    coverage = [row.hotspot_coverage for row in rows]
    eta_cap = [row.eta_cap for row in rows]
    activations = [row.activation_count for row in rows]
    windows = [row.window_count for row in rows]
    runtime_minutes = [row.runtime_seconds / 60.0 for row in rows]
    generations = [row.generations for row in rows]

    taskset_colors = ["#2f7ebc", "#ef8f35", "#4f8a5b"]
    accent = "#b7462f"
    outputs: list[Path] = []

    fig, ax = _new_figure()
    ax.bar(x, coverage, color=taskset_colors, width=0.58, edgecolor="#3a332c", linewidth=0.8)
    ax.set_xticks(x, labels)
    ax.set_ylim(0.76, 0.90)
    ax.set_title("GA在三套常态任务集上的热点覆盖率", loc="left", fontsize=15, fontweight="bold")
    ax.set_ylabel("热点覆盖率")
    ax.set_xlabel("常态任务集")
    _annotate_bars(ax, fmt="{:.3f}", dy=0.003)
    ax.text(0.0, -0.18, "说明：三套任务集的FR和平均完成率均为1.0，因此不再单独画出。", transform=ax.transAxes, fontsize=10, color="#5c5449")
    output_path = OUTPUT_DIR / "ga_hotspot_coverage_cn.png"
    _save_figure(fig, output_path)
    outputs.append(output_path)

    fig, ax = _new_figure()
    ax.bar(x, eta_cap, color=taskset_colors, width=0.58, edgecolor="#3a332c", linewidth=0.8)
    ax.set_xticks(x, labels)
    ax.set_ylim(0.0, max(eta_cap) * 1.35)
    ax.set_title("GA在三套常态任务集上的容量惩罚", loc="left", fontsize=15, fontweight="bold")
    ax.set_ylabel("eta_cap（越低越好）")
    ax.set_xlabel("常态任务集")
    _annotate_bars(ax, fmt="{:.4f}", dy=max(eta_cap) * 0.03)
    output_path = OUTPUT_DIR / "ga_capacity_penalty_cn.png"
    _save_figure(fig, output_path)
    outputs.append(output_path)

    fig, ax = _new_figure()
    width = 0.34
    bars1 = ax.bar(x - width / 2.0, windows, width=width, color="#92b4d6", edgecolor="#3a332c", linewidth=0.8, label="窗口数")
    bars2 = ax.bar(x + width / 2.0, activations, width=width, color="#3e6b89", edgecolor="#3a332c", linewidth=0.8, label="激活次数")
    ax.set_xticks(x, labels)
    ax.set_title("GA方案稀疏性", loc="left", fontsize=15, fontweight="bold")
    ax.set_ylabel("数量")
    ax.set_xlabel("常态任务集")
    ax.legend(frameon=False, loc="upper left")
    for bar in list(bars1) + list(bars2):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, height + 0.2, f"{height:.0f}", ha="center", va="bottom", fontsize=9, color="#2f2a24")
    output_path = OUTPUT_DIR / "ga_resource_sparsity_cn.png"
    _save_figure(fig, output_path)
    outputs.append(output_path)

    fig, ax = _new_figure()
    ax.bar(x, runtime_minutes, color=taskset_colors, width=0.58, edgecolor="#3a332c", linewidth=0.8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("运行时间（分钟）")
    ax.set_xlabel("常态任务集")
    ax.set_title("GA求解代价", loc="left", fontsize=15, fontweight="bold")
    _annotate_bars(ax, fmt="{:.1f}", dy=max(runtime_minutes) * 0.02)
    ax2 = ax.twinx()
    ax2.plot(x, generations, color=accent, marker="o", linewidth=2.2, markersize=7)
    ax2.set_ylabel("迭代代数", color=accent)
    ax2.tick_params(axis="y", colors=accent)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(accent)
    for xpos, gen in zip(x, generations):
        ax2.text(xpos, gen + 1.2, f"{gen}", ha="center", va="bottom", color=accent, fontsize=9)
    output_path = OUTPUT_DIR / "ga_solve_cost_cn.png"
    _save_figure(fig, output_path)
    outputs.append(output_path)
    return outputs


def build_algorithm_comparison_figures(rows: list[AlgorithmMetrics]) -> list[Path]:
    labels = sorted({row.label for row in rows}, key=["Light60", "Normal72", "Heavy84"].index)
    ga_rows = [row for row in rows if row.algorithm == "GA"]
    sg_rows = [row for row in rows if row.algorithm == "Static greedy (stop when feasible)"]

    def values(items: list[AlgorithmMetrics], field: str) -> list[float]:
        mapping = {row.label: getattr(row, field) for row in items}
        return [mapping[label] for label in labels]

    x = np.arange(len(labels))
    width = 0.33
    ga_color = "#2f7ebc"
    sg_color = "#d78745"
    outputs: list[Path] = []

    panels = [
        ("hotspot_coverage", "GA与静态贪心对比：热点覆盖率", "热点覆盖率", "{:.3f}", None, "compare_hotspot_coverage_cn.png"),
        ("eta_cap", "GA与静态贪心对比：容量惩罚", "eta_cap（越低越好）", "{:.4f}", None, "compare_capacity_penalty_cn.png"),
        ("activation_count", "GA与静态贪心对比：激活次数", "激活次数（越低越好）", "{:.0f}", None, "compare_activation_count_cn.png"),
        ("runtime_seconds", "GA与静态贪心对比：运行时间", "运行时间（秒，对数坐标）", "{:.0f}", "log", "compare_runtime_cn.png"),
    ]

    for field, title, ylabel, fmt, yscale, filename in panels:
        fig, ax = _new_figure()
        ga_vals = values(ga_rows, field)
        sg_vals = values(sg_rows, field)
        bars1 = ax.bar(x - width / 2.0, ga_vals, width=width, color=ga_color, edgecolor="#3a332c", linewidth=0.8, label="GA")
        bars2 = ax.bar(
            x + width / 2.0,
            sg_vals,
            width=width,
            color=sg_color,
            edgecolor="#3a332c",
            linewidth=0.8,
            label="静态贪心（可行即停）",
        )
        ax.set_xticks(x, labels)
        ax.set_title(title, loc="left", fontsize=15, fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.set_xlabel("常态任务集")
        if yscale == "log":
            ax.set_yscale("log")
        else:
            ymax = max(ga_vals + sg_vals)
            ax.set_ylim(0.0, ymax * 1.28 if ymax else 1.0)
        offset = (max(ga_vals + sg_vals) * 0.03) if yscale != "log" else 1.0
        for bar in list(bars1) + list(bars2):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height * (1.08 if yscale == "log" else 1.0) + (0.0 if yscale == "log" else offset),
                fmt.format(height),
                ha="center",
                va="bottom",
                fontsize=8.5,
                color="#2f2a24",
            )
        ax.legend(frameon=False, loc="upper left")
        ax.text(
            0.0,
            -0.18,
            "注：两种算法在三套任务集上的FR与平均完成率均为1.0，此处仅展示更有区分度的指标。",
            transform=ax.transAxes,
            fontsize=10,
            color="#5c5449",
        )
        output_path = OUTPUT_DIR / filename
        _save_figure(fig, output_path)
        outputs.append(output_path)
    return outputs


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ga_rows = load_ga_metrics()
    comparison_rows = load_comparison_metrics()

    outputs = []
    outputs.extend(build_ga_single_figures(ga_rows))
    outputs.extend(build_algorithm_comparison_figures(comparison_rows))

    for output in outputs:
        print(f"Saved: {output}")


if __name__ == "__main__":
    main()
