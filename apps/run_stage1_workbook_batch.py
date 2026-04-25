from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs3.scenario import load_scenario
from bs3.stage1 import run_stage1
from bs3.stage1_screening import screen_candidate_windows
from bs3.stage1_static_value import annotate_scenario_candidate_values
from bs3.stage1_taskset_runner import (
    DEFAULT_BASE_SCENARIO,
    DEFAULT_CROSS_SUMMARY,
    DEFAULT_CROSS_TIMESERIES,
    DEFAULT_DOMAIN_A_SUMMARY,
    DEFAULT_DOMAIN_A_TIMESERIES,
    DEFAULT_DOMAIN_B_SUMMARY,
    DEFAULT_DOMAIN_B_TIMESERIES,
    Stage1TasksetRunConfig,
    build_stage1_taskset_payload,
    candidate_to_dict,
    enforce_cross_distance_limit,
    json_ready_scenario_payload,
    maybe_enrich_with_distances,
    task_stats,
    write_json,
)
from bs3.stage1_visualization import export_stage1_run_artifacts


NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "results" / "stage1" / "workbook_runs"


def _float(value: Any) -> float:
    return float(value)


def _col_to_index(label: str) -> int:
    idx = 0
    for ch in label:
        if ch.isalpha():
            idx = idx * 26 + (ord(ch.upper()) - 64)
    return idx - 1


def read_xlsx_sheets(path: Path) -> dict[str, list[list[str]]]:
    sheets: dict[str, list[list[str]]] = {}
    with zipfile.ZipFile(path) as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", NS):
                parts = [node.text or "" for node in si.iterfind(".//a:t", NS)]
                shared_strings.append("".join(parts))

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"].lstrip("/") for rel in rels}

        for sheet in workbook.find("a:sheets", NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rel_map[rel_id]
            root = ET.fromstring(zf.read(target))
            rows: list[list[str]] = []
            for row in root.findall(".//a:sheetData/a:row", NS):
                values: dict[int, str] = {}
                for cell in row.findall("a:c", NS):
                    ref = cell.attrib.get("r", "")
                    match = re.match(r"([A-Z]+)(\d+)", ref)
                    if not match:
                        continue
                    idx = _col_to_index(match.group(1))
                    cell_type = cell.attrib.get("t")
                    if cell_type == "inlineStr":
                        value = "".join(node.text or "" for node in cell.iterfind(".//a:t", NS))
                    else:
                        raw = cell.find("a:v", NS)
                        if raw is None:
                            value = ""
                        elif cell_type == "s":
                            value = shared_strings[int(raw.text)]
                        else:
                            value = raw.text or ""
                    values[idx] = value
                if values:
                    max_idx = max(values)
                    rows.append([values.get(i, "") for i in range(max_idx + 1)])
            sheets[name] = rows
    return sheets


def read_task_sets(path: Path) -> tuple[list[tuple[str, str]], dict[str, list[dict[str, str]]]]:
    sheet_rows = read_xlsx_sheets(path)
    readme_rows = [(row[0], row[1] if len(row) > 1 else "") for row in sheet_rows.get("README", []) if row]
    task_sets: dict[str, list[dict[str, str]]] = {}
    for name, rows in sheet_rows.items():
        if name == "README" or not rows:
            continue
        header = rows[0]
        items: list[dict[str, str]] = []
        for row in rows[1:]:
            if not any(str(cell).strip() for cell in row):
                continue
            values = row + [""] * (len(header) - len(row))
            items.append({header[idx]: values[idx] for idx in range(len(header))})
        task_sets[name] = items
    return readme_rows, task_sets


def workbook_task_to_payload(row: dict[str, str]) -> dict[str, Any]:
    task_type = str(row.get("task_type", "reg")).strip().lower() or "reg"
    if task_type not in {"reg", "emg"}:
        task_type = "reg"
    return {
        "id": row["task_id"],
        "src": row["src_sat"],
        "dst": row["dst_sat"],
        "arrival": _float(row["arrival_sec"]),
        "deadline": _float(row["deadline_sec"]),
        "data": _float(row["data_volume_Mb"]),
        "weight": _float(row["priority_weight"]),
        "max_rate": _float(row["b_max_Mbps"]),
        "type": task_type,
        "preemption_priority": _float(row.get("preemption_priority", row["priority_weight"])),
        "task_class": row.get("task_class", ""),
        "arrival_utcg": row.get("arrival_utcg", ""),
        "deadline_utcg": row.get("deadline_utcg", ""),
        "avg_required_Mbps": _float(row["avg_required_Mbps"]) if row.get("avg_required_Mbps") else None,
        "notes": row.get("notes", ""),
    }


def _config_from_args(args: argparse.Namespace) -> Stage1TasksetRunConfig:
    return Stage1TasksetRunConfig(
        seed=args.seed,
        stage1_method=args.stage1_method,
        cap_a=args.cap_a,
        cap_b=args.cap_b,
        cap_x=args.cap_x,
        rho=args.rho,
        t_pre=args.t_pre,
        d_min=args.d_min,
        theta_cap=args.theta_cap,
        theta_hot=args.theta_hot,
        hot_hop_limit=args.hot_hop_limit,
        bottleneck_factor_alpha=args.alpha,
        eta_x=args.eta_x,
        static_value_snapshot_seconds=args.snapshot_seconds,
        candidate_pool_base_size=args.candidate_pool_base_size,
        geo_pool_size=args.geo_pool_size,
        geo_max_windows=args.geo_max_windows,
        candidate_pool_hot_fraction=args.candidate_pool_hot_fraction,
        candidate_pool_min_per_coarse_segment=args.candidate_pool_min_per_coarse_segment,
        candidate_pool_max_additional=args.candidate_pool_max_additional,
        q_eval=args.q_eval,
        omega_fr=args.omega_fr,
        omega_cap=args.omega_cap,
        omega_hot=args.omega_hot,
        elite_prune_count=args.elite_prune_count,
        grasp_iterations=args.grasp_iterations,
        grasp_rcl_ratio=args.grasp_rcl_ratio,
        grasp_seed=args.grasp_seed,
        grasp_rcl_min_size=args.grasp_rcl_min_size,
        population_size=args.population_size,
        crossover_probability=args.crossover_probability,
        mutation_probability=args.mutation_probability,
        max_generations=args.max_generations,
        stall_generations=args.stall_generations,
        top_m=args.top_m,
        max_runtime_seconds=args.max_runtime_seconds,
        disable_distance_enrichment=args.disable_distance_enrichment,
        domain_a_timeseries=args.domain_a_timeseries,
        domain_b_timeseries=args.domain_b_timeseries,
        cross_timeseries=args.cross_timeseries,
        domain_a_summary=args.domain_a_summary,
        domain_b_summary=args.domain_b_summary,
        cross_summary=args.cross_summary,
        domain_a_position=args.domain_a_position,
        domain_b_position=args.domain_b_position,
        light_speed_kmps=args.light_speed_kmps,
        intra_proc_delay_sec=args.intra_proc_delay_sec,
        cross_proc_delay_sec=args.cross_proc_delay_sec,
        max_cross_distance_km=args.max_cross_distance_km,
        export_artifacts=not args.skip_artifacts,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage1 on workbook task sheets.")
    parser.add_argument("--workbook", required=True, help="Path to the task workbook (.xlsx)")
    parser.add_argument("--base-scenario", default=str(DEFAULT_BASE_SCENARIO), help="Base scenario template JSON")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Root folder for workbook Stage1 outputs")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--stage1-method",
        choices=("ga", "static_greedy", "static_greedy_stop_when_feasible", "grasp_multi_start", "geo_greedy"),
        default="ga",
    )
    parser.add_argument("--sheets", nargs="*", default=["medium48", "stress96"])
    parser.add_argument("--cap-a", type=float, default=600.0)
    parser.add_argument("--cap-b", type=float, default=2000.0)
    parser.add_argument("--cap-x", type=float, default=1000.0)
    parser.add_argument("--rho", type=float, default=0.20)
    parser.add_argument("--t-pre", type=float, default=1800.0)
    parser.add_argument("--d-min", type=float, default=600.0)
    parser.add_argument("--theta-cap", type=float, default=0.08)
    parser.add_argument("--theta-hot", type=float, default=0.80)
    parser.add_argument("--hot-hop-limit", type=int, default=4)
    parser.add_argument("--alpha", type=float, default=0.85)
    parser.add_argument("--eta-x", type=float, default=0.90)
    parser.add_argument("--snapshot-seconds", type=int, default=600)
    parser.add_argument("--candidate-pool-base-size", type=int, default=400)
    parser.add_argument("--geo-pool-size", type=int, default=400)
    parser.add_argument("--geo-max-windows", type=int, default=12)
    parser.add_argument("--candidate-pool-hot-fraction", type=float, default=0.30)
    parser.add_argument("--candidate-pool-min-per-coarse-segment", type=int, default=3)
    parser.add_argument("--candidate-pool-max-additional", type=int, default=150)
    parser.add_argument("--q-eval", type=int, default=4)
    parser.add_argument("--omega-fr", type=float, default=4.0 / 9.0)
    parser.add_argument("--omega-cap", type=float, default=3.0 / 9.0)
    parser.add_argument("--omega-hot", type=float, default=2.0 / 9.0)
    parser.add_argument("--elite-prune-count", type=int, default=6)
    parser.add_argument("--grasp-iterations", type=int, default=30)
    parser.add_argument("--grasp-rcl-ratio", type=float, default=0.10)
    parser.add_argument("--grasp-seed", type=int, default=None)
    parser.add_argument("--grasp-rcl-min-size", type=int, default=None)
    parser.add_argument("--population-size", type=int, default=60)
    parser.add_argument("--crossover-probability", type=float, default=0.90)
    parser.add_argument("--mutation-probability", type=float, default=0.20)
    parser.add_argument("--max-generations", type=int, default=100)
    parser.add_argument("--stall-generations", type=int, default=20)
    parser.add_argument("--top-m", type=int, default=5)
    parser.add_argument("--max-runtime-seconds", type=float, default=None)
    parser.add_argument("--skip-artifacts", action="store_true")
    parser.add_argument("--disable-distance-enrichment", action="store_true")
    parser.add_argument("--domain-a-timeseries", default=str(DEFAULT_DOMAIN_A_TIMESERIES))
    parser.add_argument("--domain-b-timeseries", default=str(DEFAULT_DOMAIN_B_TIMESERIES))
    parser.add_argument("--cross-timeseries", default=str(DEFAULT_CROSS_TIMESERIES))
    parser.add_argument("--domain-a-summary", default=str(DEFAULT_DOMAIN_A_SUMMARY))
    parser.add_argument("--domain-b-summary", default=str(DEFAULT_DOMAIN_B_SUMMARY))
    parser.add_argument("--cross-summary", default=str(DEFAULT_CROSS_SUMMARY))
    parser.add_argument("--domain-a-position")
    parser.add_argument("--domain-b-position")
    parser.add_argument("--light-speed-kmps", type=float, default=299792.458)
    parser.add_argument("--intra-proc-delay-sec", type=float, default=0.0002)
    parser.add_argument("--cross-proc-delay-sec", type=float, default=0.0010)
    parser.add_argument("--max-cross-distance-km", type=float, default=5000.0)
    args = parser.parse_args()

    config = _config_from_args(args)
    workbook_path = Path(args.workbook)
    base_scenario_path = Path(args.base_scenario)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    base_payload = json.loads(base_scenario_path.read_text(encoding="utf-8-sig"))
    readme_rows, task_sets = read_task_sets(workbook_path)

    readme_path = output_root / "README_extracted.tsv"
    readme_path.write_text("\n".join(f"{key}\t{value}" for key, value in readme_rows), encoding="utf-8")

    requested_sheets = [name for name in args.sheets if name in task_sets]
    summary: dict[str, Any] = {
        "workbook": str(workbook_path),
        "base_scenario": str(base_scenario_path),
        "output_root": str(output_root),
        "seed": config.seed,
        "stage1_method": config.stage1_method,
        "readme_file": str(readme_path),
        "runs": [],
    }

    for sheet_name in requested_sheets:
        set_dir = output_root / sheet_name
        set_dir.mkdir(parents=True, exist_ok=True)

        workbook_rows = task_sets[sheet_name]
        tasks = [workbook_task_to_payload(row) for row in workbook_rows]
        stats = task_stats(tasks)

        tasks_path = set_dir / f"{sheet_name}_tasks.json"
        write_json(tasks_path, tasks)

        raw_payload = build_stage1_taskset_payload(
            base_payload,
            taskset_source_name=workbook_path.name,
            task_source_path=workbook_path,
            tasks=tasks,
            config=config,
            runner_name="apps/run_stage1_workbook_batch.py",
            source_metadata_key="taskset_workbook",
        )
        raw_payload["metadata"].update(
            {
                "name": f"stage1-taskset-{sheet_name}",
                "taskset_sheet": sheet_name,
            }
        )

        raw_scenario_path = set_dir / f"{sheet_name}_scenario_input.json"
        write_json(raw_scenario_path, raw_payload)

        scenario = load_scenario(raw_scenario_path)
        scenario, enrich_stats = maybe_enrich_with_distances(scenario, config)
        enforce_cross_distance_limit(scenario, config.max_cross_distance_km)

        weighted_scenario_path = None
        if enrich_stats is not None:
            weighted_scenario_path = set_dir / f"{sheet_name}_scenario_weighted.json"
            write_json(weighted_scenario_path, json_ready_scenario_payload(scenario))

        if config.stage1_method.strip().lower() == "geo_greedy":
            scenario.metadata.setdefault("_runtime_cache", {})["raw_candidate_windows"] = list(scenario.candidate_windows)
        else:
            annotate_scenario_candidate_values(scenario, force=True)
            screen_candidate_windows(scenario)

        annotated_scenario_path = set_dir / f"{sheet_name}_scenario_annotated.json"
        write_json(annotated_scenario_path, json_ready_scenario_payload(scenario))

        started = time.perf_counter()
        result = run_stage1(scenario, seed=config.seed, method=config.stage1_method)
        elapsed = time.perf_counter() - started

        artifacts = {}
        if config.export_artifacts:
            artifacts = export_stage1_run_artifacts(scenario, result.best_feasible, set_dir, sheet_name)

        baseline_trace_payload = asdict(result.baseline_trace) if result.baseline_trace is not None else None
        baseline_trace_file = None
        if baseline_trace_payload is not None:
            baseline_trace_file = set_dir / f"{sheet_name}_baseline_trace.json"
            write_json(baseline_trace_file, baseline_trace_payload)

        result_payload = {
            "sheet": sheet_name,
            "seed": config.seed,
            "stage1_method": result.stage1_method,
            "runtime_seconds": elapsed,
            "generations": result.generations,
            "selected_plan": [asdict(window) for window in result.selected_plan],
            "selected_solution": candidate_to_dict(result.selected_solution) if result.selected_solution else None,
            "best_feasible": [candidate_to_dict(candidate) for candidate in result.best_feasible],
            "population_best": candidate_to_dict(result.population_best) if result.population_best else None,
            "baseline_summary": dict(result.baseline_summary),
            "baseline_trace_file": (baseline_trace_file.name if baseline_trace_file is not None else None),
            "baseline_trace": baseline_trace_payload,
            "used_feedback": result.used_feedback,
            "timed_out": result.timed_out,
            "elapsed_seconds": result.elapsed_seconds,
            "task_stats": stats,
            "stage1_screening": scenario.metadata.get("stage1_screening", {}),
            "stage1_geo_screening": scenario.metadata.get("stage1_geo_screening", {}),
            "distance_enrichment": enrich_stats,
            "artifacts": artifacts,
        }
        result_path = set_dir / f"{sheet_name}_stage1_result.json"
        write_json(result_path, result_payload)

        best = result.selected_solution
        run_record = {
            "sheet": sheet_name,
            "stage1_method": result.stage1_method,
            "result_file": str(result_path),
            "baseline_trace_file": str(baseline_trace_file) if baseline_trace_file is not None else None,
            "task_stats": stats,
            "runtime_seconds": elapsed,
            "timed_out": result.timed_out,
            "generations": result.generations,
            "feasible_count": len(result.best_feasible),
            "stage1_screening": scenario.metadata.get("stage1_screening", {}),
            "stage1_geo_screening": scenario.metadata.get("stage1_geo_screening", {}),
            "distance_enrichment": enrich_stats,
            "artifacts": artifacts,
            "best_summary": (
                {
                    "mean_completion_ratio": best.mean_completion_ratio,
                    "fr": best.fr,
                    "eta_cap": best.eta_cap,
                    "eta_0": best.eta_0,
                    "hotspot_coverage": best.hotspot_coverage,
                    "hotspot_max_gap": best.hotspot_max_gap,
                    "gateway_count": best.gateway_count,
                    "window_count": best.window_count,
                    "activation_count": best.activation_count,
                    "max_cross_gap": best.max_cross_gap,
                    "cross_active_fraction": best.cross_active_fraction,
                }
                if best is not None
                else None
            ),
        }
        summary["runs"].append(run_record)

    summary_path = output_root / "batch_summary.json"
    write_json(summary_path, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
