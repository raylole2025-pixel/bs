# BS3 Two-Stage Scheduler

BS3 runs a two-stage cross-domain scheduling workflow:

1. Stage1 selects and activates cross-domain windows for regular tasks.
2. Stage2 replays the fixed Stage1 window plan and inserts emergency traffic with controlled preemption and recovery.

The default Stage1 workflow is:

1. read a regular-task JSON file
2. merge it into the shared scenario template
3. enrich link distance and delay data when configured
4. compute candidate-window static values and run candidate screening
5. run the Stage1 GA and export feasible activation plans plus baseline trace artifacts for Stage2

## Quick Start

Run Stage1 directly from a taskset JSON file:

```bash
python apps/run_stage1_json_taskset.py path/to/regular_tasks.json --seed 7
```

Run the full Stage1 -> Stage2 pipeline on a prepared scenario JSON file:

```bash
python apps/run_scenario_pipeline.py examples/sample_scenario.json --seed 7 --output result.json
```

Run Stage2 on a fixed Stage1 result plus a mixed regular/emergency task JSON:

```bash
python tools/run_stage2_fixed_stage1_smoke.py --base-scenario examples/sample_scenario.json --stage1-result path/to/stage1_result.json --task-json path/to/mixed_tasks.json
```

## Repository Layout

```text
bs3/
|- apps/                  main entry scripts
|- tools/                 analysis and helper scripts
|- bs3/                   core package
|- examples/              minimal runnable examples
|- inputs/                reusable Stage1 base template
|- mydata/
|  |- constellation/      constellation notes
|  |- stk_access/         raw STK access exports
|  |- distances/          reusable distance products
|  `- topology/           reusable topology assets
|- results/               retained Stage1/Stage2 outputs
|- docs/                  project docs
`- tests/                 regression tests
```

## Common Entry Points

- `apps/run_stage1_json_taskset.py`
- `apps/run_scenario_pipeline.py`
- `apps/run_stage2_workbook_sheet.py`
- `apps/preprocess_stk_access.py`
- `apps/build_stage1_template_from_preprocess.py`
- `apps/run_stage1_workbook_batch.py`
- `tools/run_stage2_emergency_validation.py`
- `tools/run_stage2_fixed_stage1_smoke.py`
- `tools/enrich_scenario_distances.py`

## Important Default Paths

- Base scenario template: `inputs/templates/stage1_scenario_template.json`
- `inputs/` no longer stores canonical tasksets; retained runnable results live under `results/`
- Distance data: `mydata/distances/`
- Default Stage1 JSON outputs: `results/stage1/json_taskset_runs/`
- Default Stage1 workbook outputs: `results/stage1/workbook_runs/`
- Default Stage2 outputs: `results/stage2/`
- Canonical retained results: `results/stage1/{light,normal,heavy}` and `results/stage2/normal/{smoke,adversarial,stress}`

## Parameter Documentation

- Canonical parameter table: `docs/PARAMETER_SETTINGS.md`
- 4.6 alignment checklist: `docs/ALIGNMENT_CHECK_4_6.md`
