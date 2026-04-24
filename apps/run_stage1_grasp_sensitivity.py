from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs3.scenario import load_scenario
from bs3.stage1 import run_stage1
from bs3.stage1_taskset_runner import candidate_to_dict, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = PROJECT_ROOT / "results" / "stage1" / "normal" / "normal_scenario_weighted.json"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "results" / "stage1" / "grasp_sensitivity"
DEFAULT_ITERATIONS = (10, 30, 50)
DEFAULT_RATIOS = (0.05, 0.10, 0.20)


def _parse_int_list(raw: str) -> list[int]:
    return [int(item.strip()) for item in str(raw).split(",") if item.strip()]


def _parse_float_list(raw: str) -> list[float]:
    return [float(item.strip()) for item in str(raw).split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small GRASP sensitivity sweep on one weighted Stage1 scenario.")
    parser.add_argument("--scenario", default=str(DEFAULT_SCENARIO), help="Weighted scenario JSON to evaluate")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Root folder for sweep outputs")
    parser.add_argument("--seed", type=int, default=7, help="Stage1 seed")
    parser.add_argument("--grasp-seed", type=int, default=7, help="GRASP construction seed")
    parser.add_argument("--iterations", default="10,30,50", help="Comma-separated grasp_iterations values")
    parser.add_argument("--rcl-ratios", default="0.05,0.10,0.20", help="Comma-separated grasp_rcl_ratio values")
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    iterations_list = _parse_int_list(args.iterations) or list(DEFAULT_ITERATIONS)
    ratio_list = _parse_float_list(args.rcl_ratios) or list(DEFAULT_RATIOS)
    method = "grasp_multi_start"

    rows: list[dict[str, object]] = []
    for iterations in iterations_list:
        for ratio in ratio_list:
            started = time.perf_counter()
            scenario = load_scenario(scenario_path)
            scenario.stage1 = replace(
                scenario.stage1,
                grasp_iterations=int(iterations),
                grasp_rcl_ratio=float(ratio),
                grasp_seed=int(args.grasp_seed),
            )
            result = run_stage1(scenario, seed=args.seed, method=method)
            wall_clock = time.perf_counter() - started

            result_stem = f"normal_grasp_it{int(iterations)}_rcl{float(ratio):.2f}".replace(".", "p")
            result_file = output_root / f"{result_stem}_result.json"
            result_payload = {
                "scenario_file": str(scenario_path.resolve()),
                "seed": args.seed,
                "grasp_seed": args.grasp_seed,
                "stage1_method": result.stage1_method,
                "grasp_iterations": int(iterations),
                "grasp_rcl_ratio": float(ratio),
                "selected_plan": [asdict(window) for window in result.selected_plan],
                "selected_solution": candidate_to_dict(result.selected_solution) if result.selected_solution else None,
                "best_feasible": [candidate_to_dict(candidate) for candidate in result.best_feasible],
                "population_best": candidate_to_dict(result.population_best) if result.population_best else None,
                "baseline_summary": dict(result.baseline_summary),
                "baseline_trace": asdict(result.baseline_trace) if result.baseline_trace is not None else None,
                "elapsed_seconds": result.elapsed_seconds,
                "wall_clock_seconds": wall_clock,
                "timed_out": result.timed_out,
                "history": result.history,
                "stage1_screening": scenario.metadata.get("stage1_screening", {}),
            }
            write_json(result_file, result_payload)

            best = result.selected_solution
            rows.append(
                {
                    "scenario_file": str(scenario_path.resolve()),
                    "stage1_method": result.stage1_method,
                    "grasp_iterations": int(iterations),
                    "grasp_rcl_ratio": float(ratio),
                    "grasp_seed": int(args.grasp_seed),
                    "fr": (best.fr if best is not None else None),
                    "mean_completion_ratio": (best.mean_completion_ratio if best is not None else None),
                    "window_count": (best.window_count if best is not None else None),
                    "activation_count": (best.activation_count if best is not None else None),
                    "avg_hot_coverage": (best.avg_hot_coverage if best is not None else None),
                    "eta_cap": (best.eta_cap if best is not None else None),
                    "runtime_seconds": result.elapsed_seconds,
                    "wall_clock_seconds": wall_clock,
                    "timed_out": result.timed_out,
                    "result_file": str(result_file.resolve()),
                }
            )
            print(
                f"done iterations={int(iterations)} rcl_ratio={float(ratio):.2f} runtime={result.elapsed_seconds:.2f}s",
                flush=True,
            )

    rows.sort(key=lambda item: (int(item["grasp_iterations"]), float(item["grasp_rcl_ratio"])))
    summary_payload = {
        "scenario_file": str(scenario_path.resolve()),
        "stage1_method": method,
        "seed": args.seed,
        "grasp_seed": args.grasp_seed,
        "iterations": iterations_list,
        "rcl_ratios": ratio_list,
        "rows": rows,
    }
    summary_json = output_root / "grasp_sensitivity_summary.json"
    write_json(summary_json, summary_payload)

    summary_csv = output_root / "grasp_sensitivity_summary.csv"
    with summary_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "grasp_iterations",
                "grasp_rcl_ratio",
                "grasp_seed",
                "fr",
                "mean_completion_ratio",
                "window_count",
                "activation_count",
                "avg_hot_coverage",
                "eta_cap",
                "runtime_seconds",
                "wall_clock_seconds",
                "timed_out",
                "result_file",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})

    print(f"summary_json={summary_json.resolve()}", flush=True)
    print(f"summary_csv={summary_csv.resolve()}", flush=True)


if __name__ == "__main__":
    main()
