from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs3.stage1_taskset_runner import (
    DEFAULT_BASE_SCENARIO,
    DEFAULT_CROSS_SUMMARY,
    DEFAULT_CROSS_TIMESERIES,
    DEFAULT_DOMAIN_A_SUMMARY,
    DEFAULT_DOMAIN_A_TIMESERIES,
    DEFAULT_DOMAIN_B_SUMMARY,
    DEFAULT_DOMAIN_B_TIMESERIES,
    DEFAULT_JSON_OUTPUT_ROOT,
    Stage1TasksetRunConfig,
    run_stage1_on_taskset_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage1 directly from a regular-task JSON file.")
    parser.add_argument("taskset_json", help="Path to a taskset JSON file (list or {'tasks': [...]})")
    parser.add_argument("--base-scenario", default=str(DEFAULT_BASE_SCENARIO), help="Base scenario template JSON")
    parser.add_argument("--output-root", default=str(DEFAULT_JSON_OUTPUT_ROOT), help="Root folder for Stage1 outputs")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--stage1-method",
        choices=("ga", "static_greedy", "static_greedy_stop_when_feasible", "grasp_multi_start"),
        default="ga",
    )
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
    parser.add_argument("--completion-tolerance", type=float, default=1e-6)
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

    config = Stage1TasksetRunConfig(
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
        completion_tolerance=args.completion_tolerance,
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

    summary = run_stage1_on_taskset_json(
        args.taskset_json,
        base_scenario_path=args.base_scenario,
        output_root=args.output_root,
        config=config,
        runner_name="apps/run_stage1_json_taskset.py",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
