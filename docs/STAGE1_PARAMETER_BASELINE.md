# Stage1 Parameter Baseline

> This file is kept for historical context.  
> The canonical parameter document is `docs/PARAMETER_SETTINGS.md`.

This file records the current Stage1 baseline after the 2026-04-06 rewrite.

The formal Stage1 metric set follows the "阶段一4.6" definition:

- feasibility constraints: `SR_{theta_c}`, `eta_cap`, `hotspot_coverage`
- feasible-plan ranking: `N_act`, `SR_{theta_c}`, `eta_cap`, `hotspot_coverage`
- `f_reg` is no longer part of the formal Stage1 metric set

## Core Thresholds

- `theta_sr = 0.90`
- `theta_cap = 0.08`
- `theta_hot = 0.80`
- `theta_c = 0.95`

## Core Capacity and Window Parameters

- `rho = 0.20`
- `t_pre = 1800 s`
- `d_min = 600 s`
- `hot_hop_limit = 4`
- `bottleneck_factor_alpha = 0.85`
- `eta_x = 0.90`
- `static_value_snapshot_seconds = 600`
- `q_eval = 4`

## Violation Aggregation Weights

- `omega_sr = 4 / 9`
- `omega_cap = 3 / 9`
- `omega_hot = 2 / 9`

## GA Defaults

- `population_size = 60`
- `crossover_probability = 0.90`
- `mutation_probability = 0.20`
- `max_generations = 100`
- `stall_generations = 20`
- `top_m = 5`
- `elite_prune_count = 6`

Derived inside the implementation:

- `elite_count = ceil(0.1P)`
- `immigrant_count = ceil(0.1P)`
- RCL size per step: `max(5, ceil(0.1 * remaining_windows))`
- Tournament size: `3`
- Exact pruning candidate cap per round: `8`

## Workbook Runner Defaults

These defaults are set in [run_stage1_workbook_batch.py](/D:/Codex_Project/bs3/apps/run_stage1_workbook_batch.py):

- `C_A = 600 Mbps`
- `C_B = 2000 Mbps`
- `C_X = 1000 Mbps`
- `screen_pool_size = 450`
- `screen_block_seconds = 900`
- `max_cross_distance_km = 5000`
- `stage2_k_paths = 2`
- `intra_proc_delay_sec = 0.0002`
- `cross_proc_delay_sec = 0.0010`
