# BS3 Parameter Reference

> This file is kept for historical context.  
> The canonical parameter document is `docs/PARAMETER_SETTINGS.md`.

This is a trimmed parameter reference aligned to the cleaned repository layout on 2026-04-22.

## Parameter Sources

When values disagree, read them in this order:

1. The retained scenario/result files under `results/`
2. The defaults inside `apps/` and `tools/` entry scripts
3. Runtime fallback defaults in `bs3/scenario.py`

## Retained Scenario References

Current retained Stage1 results:

- `results/stage1/light/`
- `results/stage1/normal/`
- `results/stage1/heavy/`

Current retained Stage2 results:

- `results/stage2/normal/smoke/`
- `results/stage2/normal/adversarial/`
- `results/stage2/normal/stress/`

## Default Script Locations

- Stage 1 JSON taskset runner: `apps/run_stage1_json_taskset.py`
- Stage 1 batch runner: `apps/run_stage1_workbook_batch.py`
- Stage 2 workbook runner: `apps/run_stage2_workbook_sheet.py`
- Preprocess entry: `apps/preprocess_stk_access.py`
- Scenario-template builder: `apps/build_stage1_template_from_preprocess.py`
- Distance enrichment tool: `tools/enrich_scenario_distances.py`
- Stage 2 fixed-plan runner: `tools/run_stage2_fixed_stage1_smoke.py`
- Stage 2 validation runner: `tools/run_stage2_emergency_validation.py`

## Default Input and Output Paths

`apps/run_stage1_workbook_batch.py`:

- base scenario: `inputs/templates/stage1_scenario_template.json`
- output root: `results/stage1/workbook_runs`
- distance root: `mydata/distances/`

`apps/run_stage1_json_taskset.py`:

- base scenario: `inputs/templates/stage1_scenario_template.json`
- output root: `results/stage1/json_taskset_runs`
- distance root: `mydata/distances/`

`tools/run_stage2_fixed_stage1_smoke.py` and `tools/run_stage2_emergency_validation.py`:

- output root: `results/stage2/`

`apps/preprocess_stk_access.py`:

- output dir: `mydata/topology/stage1_preprocess_user`

`apps/build_stage1_template_from_preprocess.py`:

- default output: `inputs/templates/stage1_scenario_template.json`

## Distance Files

The current default distance products are:

- `mydata/distances/domain1_isl_distance_20260323/domain1_isl_distance_timeseries.csv`
- `mydata/distances/domain2_isl_distance_20260323/domain2_isl_distance_timeseries.csv`
- `mydata/distances/crosslink_distance_20260323/crosslink_distance_timeseries.csv`
- `mydata/distances/domain1_isl_distance_20260323/domain1_isl_pair_summary.csv`
- `mydata/distances/domain2_isl_distance_20260323/domain2_isl_pair_summary.csv`
- `mydata/distances/crosslink_distance_20260323/crosslink_pair_summary.csv`

## Active Stage 1 Baseline

For the current Stage1 baseline, see `docs/STAGE1_PARAMETER_BASELINE.md`.

For the full parameter-by-parameter table with source locations and meanings, see `docs/CURRENT_PARAMETER_TABLE.md`.
