from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import json
import time
from pathlib import Path
from typing import Any

from .distance_enrichment import enrich_scenario_distances
from .scenario import load_scenario, scenario_to_dict
from .stage1 import run_stage1
from .stage1_screening import screen_candidate_windows
from .stage1_static_value import annotate_scenario_candidate_values
from .stage1_visualization import export_stage1_run_artifacts


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_SCENARIO = PROJECT_ROOT / "inputs" / "templates" / "stage1_scenario_template.json"
DEFAULT_JSON_OUTPUT_ROOT = PROJECT_ROOT / "results" / "stage1" / "json_taskset_runs"
DEFAULT_DISTANCE_ROOT = PROJECT_ROOT / "mydata" / "distances"
DEFAULT_DOMAIN_A_TIMESERIES = DEFAULT_DISTANCE_ROOT / "domain1_isl_distance_20260323" / "domain1_isl_distance_timeseries.csv"
DEFAULT_DOMAIN_B_TIMESERIES = DEFAULT_DISTANCE_ROOT / "domain2_isl_distance_20260323" / "domain2_isl_distance_timeseries.csv"
DEFAULT_CROSS_TIMESERIES = DEFAULT_DISTANCE_ROOT / "crosslink_distance_20260323" / "crosslink_distance_timeseries.csv"
DEFAULT_DOMAIN_A_SUMMARY = DEFAULT_DISTANCE_ROOT / "domain1_isl_distance_20260323" / "domain1_isl_pair_summary.csv"
DEFAULT_DOMAIN_B_SUMMARY = DEFAULT_DISTANCE_ROOT / "domain2_isl_distance_20260323" / "domain2_isl_pair_summary.csv"
DEFAULT_CROSS_SUMMARY = DEFAULT_DISTANCE_ROOT / "crosslink_distance_20260323" / "crosslink_pair_summary.csv"


@dataclass(frozen=True)
class Stage1TasksetRunConfig:
    seed: int = 7
    stage1_method: str = "ga"
    cap_a: float = 600.0
    cap_b: float = 2000.0
    cap_x: float = 1000.0
    rho: float = 0.20
    t_pre: float = 1800.0
    d_min: float = 600.0
    theta_cap: float = 0.08
    theta_hot: float = 0.80
    hot_hop_limit: int = 4
    bottleneck_factor_alpha: float = 0.85
    eta_x: float = 0.90
    static_value_snapshot_seconds: int = 600
    candidate_pool_base_size: int = 400
    geo_pool_size: int | None = None
    geo_max_windows: int = 12
    candidate_pool_hot_fraction: float = 0.30
    enable_hotspot_metrics: bool = True
    candidate_pool_min_per_coarse_segment: int = 3
    candidate_pool_max_additional: int = 150
    q_eval: int = 4
    omega_fr: float = 4.0 / 9.0
    omega_cap: float = 3.0 / 9.0
    omega_hot: float = 2.0 / 9.0
    elite_prune_count: int = 6
    grasp_iterations: int = 30
    grasp_rcl_ratio: float = 0.10
    grasp_seed: int | None = None
    grasp_rcl_min_size: int | None = None
    population_size: int = 60
    crossover_probability: float = 0.90
    mutation_probability: float = 0.20
    max_generations: int = 100
    stall_generations: int = 20
    top_m: int = 5
    max_runtime_seconds: float | None = None
    completion_tolerance: float = 1e-6
    disable_distance_enrichment: bool = False
    domain_a_timeseries: str = str(DEFAULT_DOMAIN_A_TIMESERIES)
    domain_b_timeseries: str = str(DEFAULT_DOMAIN_B_TIMESERIES)
    cross_timeseries: str = str(DEFAULT_CROSS_TIMESERIES)
    domain_a_summary: str = str(DEFAULT_DOMAIN_A_SUMMARY)
    domain_b_summary: str = str(DEFAULT_DOMAIN_B_SUMMARY)
    cross_summary: str = str(DEFAULT_CROSS_SUMMARY)
    domain_a_position: str | None = None
    domain_b_position: str | None = None
    light_speed_kmps: float = 299792.458
    intra_proc_delay_sec: float = 0.0002
    cross_proc_delay_sec: float = 0.0010
    max_cross_distance_km: float | None = 5000.0
    export_artifacts: bool = False


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_taskset_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("tasks"), list):
        return payload["tasks"]
    raise ValueError(f"Unsupported taskset JSON structure in {path}")


def candidate_to_dict(candidate) -> dict[str, Any]:
    data = asdict(candidate)
    data["fr"] = candidate.fr
    data["mean_completion_ratio"] = candidate.mean_completion_ratio
    data["hotspot_coverage"] = data.get("avg_hot_coverage")
    data["hotspot_max_gap"] = data.get("max_hot_gap")
    data["plan"] = [asdict(window) for window in candidate.plan]
    return data


def json_ready_scenario_payload(scenario) -> dict[str, Any]:
    payload = scenario_to_dict(scenario)
    metadata = dict(payload.get("metadata", {}))
    metadata.pop("_runtime_cache", None)
    payload["metadata"] = metadata
    return payload


def task_stats(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    if not tasks:
        return {
            "count": 0,
            "total_data_Mb": 0.0,
            "weighted_average_priority": 0.0,
            "peak_concurrency": 0,
            "peak_avg_required_Mbps": 0.0,
            "min_window_s": 0.0,
            "max_window_s": 0.0,
            "mean_window_s": 0.0,
        }

    events: list[tuple[float, int, float]] = []
    durations: list[float] = []
    total_weight = 0.0
    weighted_priority = 0.0
    total_data = 0.0
    for task in tasks:
        arrival = float(task["arrival"])
        deadline = float(task["deadline"])
        avg_required = float(task.get("avg_required_Mbps") or (task["data"] / max(deadline - arrival, 1e-9)))
        duration = deadline - arrival
        durations.append(duration)
        total_data += float(task["data"])
        total_weight += 1.0
        weighted_priority += float(task["weight"])
        events.append((arrival, 1, avg_required))
        events.append((deadline, -1, avg_required))

    events.sort(key=lambda item: (item[0], -item[1]))
    active = 0
    active_avg = 0.0
    peak_concurrency = 0
    peak_avg = 0.0
    for _, delta, avg_required in events:
        if delta > 0:
            active += 1
            active_avg += avg_required
        else:
            active -= 1
            active_avg -= avg_required
        peak_concurrency = max(peak_concurrency, active)
        peak_avg = max(peak_avg, active_avg)

    return {
        "count": len(tasks),
        "total_data_Mb": total_data,
        "weighted_average_priority": weighted_priority / max(total_weight, 1.0),
        "peak_concurrency": peak_concurrency,
        "peak_avg_required_Mbps": peak_avg,
        "min_window_s": min(durations),
        "max_window_s": max(durations),
        "mean_window_s": sum(durations) / len(durations),
    }


def build_stage1_taskset_payload(
    base_payload: dict[str, Any],
    *,
    taskset_source_name: str,
    task_source_path: Path,
    tasks: list[dict[str, Any]],
    config: Stage1TasksetRunConfig,
    runner_name: str,
    source_metadata_key: str = "taskset_json",
) -> dict[str, Any]:
    payload = deepcopy(base_payload)
    payload.setdefault("metadata", {})
    payload["metadata"].update(
        {
            "name": f"stage1-taskset-{task_source_path.stem}",
            "source": taskset_source_name,
            source_metadata_key: str(task_source_path.resolve()),
            "task_units": {"data": "Mb", "rate": "Mbps"},
            "runner": runner_name,
            "seed": config.seed,
            "stage1_method": config.stage1_method,
        }
    )
    payload["capacities"] = {"A": config.cap_a, "B": config.cap_b, "X": config.cap_x}
    payload["stage1"] = {
        "rho": config.rho,
        "t_pre": config.t_pre,
        "d_min": config.d_min,
        "theta_cap": config.theta_cap,
        "theta_hot": config.theta_hot,
        "hot_hop_limit": config.hot_hop_limit,
        "bottleneck_factor_alpha": config.bottleneck_factor_alpha,
        "eta_x": config.eta_x,
        "static_value_snapshot_seconds": config.static_value_snapshot_seconds,
        "candidate_pool_base_size": config.candidate_pool_base_size,
        "geo_pool_size": config.geo_pool_size,
        "geo_max_windows": config.geo_max_windows,
        "candidate_pool_hot_fraction": config.candidate_pool_hot_fraction,
        "enable_hotspot_metrics": config.enable_hotspot_metrics,
        "candidate_pool_min_per_coarse_segment": config.candidate_pool_min_per_coarse_segment,
        "candidate_pool_max_additional": config.candidate_pool_max_additional,
        "q_eval": config.q_eval,
        "omega_fr": config.omega_fr,
        "omega_cap": config.omega_cap,
        "omega_hot": config.omega_hot,
        "elite_prune_count": config.elite_prune_count,
        "grasp_iterations": config.grasp_iterations,
        "grasp_rcl_ratio": config.grasp_rcl_ratio,
        "grasp_seed": config.grasp_seed,
        "grasp_rcl_min_size": config.grasp_rcl_min_size,
        "completion_tolerance": config.completion_tolerance,
        "ga": {
            "population_size": config.population_size,
            "crossover_probability": config.crossover_probability,
            "mutation_probability": config.mutation_probability,
            "max_generations": config.max_generations,
            "stall_generations": config.stall_generations,
            "top_m": config.top_m,
            "max_runtime_seconds": config.max_runtime_seconds,
        },
    }
    payload["tasks"] = tasks
    for window in payload.get("candidate_windows", []):
        if "value" in window:
            window["value"] = None
    return payload


def maybe_enrich_with_distances(scenario, config: Stage1TasksetRunConfig) -> tuple[Any, dict[str, Any] | None]:
    if config.disable_distance_enrichment:
        return scenario, None

    required = [config.domain_a_timeseries, config.domain_b_timeseries, config.cross_timeseries]
    if any(not item for item in required):
        return scenario, None

    scenario, stats = enrich_scenario_distances(
        scenario,
        domain_a_timeseries_csv=config.domain_a_timeseries,
        domain_b_timeseries_csv=config.domain_b_timeseries,
        cross_timeseries_csv=config.cross_timeseries,
        domain_a_pair_summary_csv=config.domain_a_summary,
        domain_b_pair_summary_csv=config.domain_b_summary,
        cross_pair_summary_csv=config.cross_summary,
        domain_a_position_file=config.domain_a_position,
        domain_b_position_file=config.domain_b_position,
        light_speed_km_per_s=config.light_speed_kmps,
        intra_proc_delay_s=config.intra_proc_delay_sec,
        cross_proc_delay_s=config.cross_proc_delay_sec,
    )
    return scenario, stats


def enforce_cross_distance_limit(scenario, max_cross_distance_km: float | None) -> None:
    if max_cross_distance_km in {None, 0, 0.0}:
        return

    kept = []
    dropped = 0
    for window in scenario.candidate_windows:
        if window.distance_km is not None and window.distance_km > max_cross_distance_km:
            dropped += 1
            continue
        kept.append(window)
    scenario.candidate_windows = kept
    scenario.metadata.setdefault("stage1_constraints", {})
    scenario.metadata["stage1_constraints"]["max_cross_distance_km"] = max_cross_distance_km
    scenario.metadata["stage1_constraints"]["dropped_candidate_window_count"] = dropped


def run_stage1_on_taskset_json(
    taskset_json_path: str | Path,
    *,
    base_scenario_path: str | Path = DEFAULT_BASE_SCENARIO,
    output_root: str | Path = DEFAULT_JSON_OUTPUT_ROOT,
    config: Stage1TasksetRunConfig | None = None,
    runner_name: str = "apps/run_stage1_json_taskset.py",
) -> dict[str, Any]:
    config = config or Stage1TasksetRunConfig()
    taskset_json_path = Path(taskset_json_path)
    base_scenario_path = Path(base_scenario_path)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    base_payload = json.loads(base_scenario_path.read_text(encoding="utf-8-sig"))
    tasks = load_taskset_json(taskset_json_path)
    stats = task_stats(tasks)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / f"{taskset_json_path.stem}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_payload = build_stage1_taskset_payload(
        base_payload,
        taskset_source_name=taskset_json_path.name,
        task_source_path=taskset_json_path,
        tasks=tasks,
        config=config,
        runner_name=runner_name,
    )

    tasks_path = run_dir / f"{taskset_json_path.stem}_tasks.json"
    write_json(tasks_path, tasks)

    raw_scenario_path = run_dir / f"{taskset_json_path.stem}_scenario_input.json"
    write_json(raw_scenario_path, raw_payload)

    scenario = load_scenario(raw_scenario_path)
    scenario, enrich_stats = maybe_enrich_with_distances(scenario, config)
    enforce_cross_distance_limit(scenario, config.max_cross_distance_km)

    weighted_scenario_path = None
    if enrich_stats is not None:
        weighted_scenario_path = run_dir / f"{taskset_json_path.stem}_scenario_weighted.json"
        write_json(weighted_scenario_path, json_ready_scenario_payload(scenario))

    if config.stage1_method.strip().lower() == "geo_greedy":
        scenario.metadata.setdefault("_runtime_cache", {})["raw_candidate_windows"] = list(scenario.candidate_windows)
    else:
        annotate_scenario_candidate_values(scenario, force=True)
        screen_candidate_windows(scenario)

    annotated_scenario_path = run_dir / f"{taskset_json_path.stem}_scenario_annotated.json"
    write_json(annotated_scenario_path, json_ready_scenario_payload(scenario))

    started = time.perf_counter()
    result = run_stage1(scenario, seed=config.seed, method=config.stage1_method)
    elapsed = time.perf_counter() - started

    artifacts = {}
    if config.export_artifacts:
        artifacts = export_stage1_run_artifacts(scenario, result.best_feasible, run_dir, taskset_json_path.stem)

    baseline_trace_payload = asdict(result.baseline_trace) if result.baseline_trace is not None else None
    baseline_trace_file = None
    if baseline_trace_payload is not None:
        baseline_trace_file = run_dir / f"{taskset_json_path.stem}_baseline_trace.json"
        write_json(baseline_trace_file, baseline_trace_payload)

    result_payload = {
        "taskset_json": str(taskset_json_path.resolve()),
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
    result_path = run_dir / f"{taskset_json_path.stem}_stage1_result.json"
    write_json(result_path, result_payload)

    best = result.selected_solution
    summary = {
        "status": "completed",
        "taskset_json": str(taskset_json_path.resolve()),
        "run_dir": str(run_dir.resolve()),
        "seed": config.seed,
        "stage1_method": result.stage1_method,
        "result_file": str(result_path.resolve()),
        "scenario_input_file": str(raw_scenario_path.resolve()),
        "scenario_weighted_file": str(weighted_scenario_path.resolve()) if weighted_scenario_path else None,
        "scenario_annotated_file": str(annotated_scenario_path.resolve()),
        "baseline_trace_file": str(baseline_trace_file.resolve()) if baseline_trace_file is not None else None,
        "runtime_seconds": elapsed,
        "timed_out": result.timed_out,
        "generations": result.generations,
        "feasible_count": len(result.best_feasible),
        "task_stats": stats,
        "stage1_screening": scenario.metadata.get("stage1_screening", {}),
        "stage1_geo_screening": scenario.metadata.get("stage1_geo_screening", {}),
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
    summary_path = run_dir / "run_summary.json"
    write_json(summary_path, summary)
    return summary


__all__ = [
    "DEFAULT_BASE_SCENARIO",
    "DEFAULT_JSON_OUTPUT_ROOT",
    "Stage1TasksetRunConfig",
    "build_stage1_taskset_payload",
    "candidate_to_dict",
    "enforce_cross_distance_limit",
    "json_ready_scenario_payload",
    "load_taskset_json",
    "maybe_enrich_with_distances",
    "run_stage1_on_taskset_json",
    "task_stats",
    "write_json",
]
