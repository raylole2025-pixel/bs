# BS3 File Guide

This repository is now organized around a cleaned Stage1 + Stage2 workflow.

## Directory Layout

```text
bs3/
|- apps/                  main entry scripts
|- tools/                 helper, validation, and analysis scripts
|- bs3/                   core Python package
|- examples/              minimal runnable examples
|- inputs/                reusable Stage1 base template
|- mydata/
|  |- constellation/      constellation notes
|  |- stk_access/         raw STK access exports
|  |- distances/          reusable distance time series and summaries
|  `- topology/           reusable topology assets
|- results/               retained Stage1/Stage2 outputs
|- docs/                  project docs
`- tests/                 regression tests
```

## Primary Workflow

- `apps/run_stage1_json_taskset.py`
  Purpose:
  Read one regular-task JSON file and produce Stage1 outputs.

- `apps/run_scenario_pipeline.py`
  Purpose:
  Run Stage1 and then Stage2 on an already prepared scenario JSON file.

- `apps/run_stage1_workbook_batch.py`
  Purpose:
  Run Stage1 on one or more workbook sheets.

- `apps/run_stage2_workbook_sheet.py`
  Purpose:
  Replay a fixed Stage1 result and run Stage2 on workbook-sourced emergency tasks.

- `apps/preprocess_stk_access.py`
  Purpose:
  Convert raw STK access exports into reusable topology assets.

- `apps/build_stage1_template_from_preprocess.py`
  Purpose:
  Build the reusable Stage1 base template from preprocess outputs.

- `tools/run_stage2_fixed_stage1_smoke.py`
  Purpose:
  Replay one fixed Stage1 plan against a mixed task JSON and only extract emergency tasks for Stage2.

- `tools/run_stage2_emergency_validation.py`
  Purpose:
  Run batch Stage2 emergency validations on top of one official Stage1 result.

## Reusable Prerequisites

- `inputs/templates/stage1_scenario_template.json`
- `mydata/distances/`
- `mydata/topology/stage1_preprocess_user/`

Notes:

- `inputs/` is still needed because `inputs/templates/stage1_scenario_template.json` is the default base template used by the Stage1 taskset runners.
- Canonical retained results now live under `results/stage1/{light,normal,heavy}` and `results/stage2/normal/{smoke,adversarial,stress}`.

## Core Stage1 Modules

- `bs3/stage1.py`
- `bs3/stage1_static_value.py`
- `bs3/stage1_screening.py`
- `bs3/scenario.py`
- `bs3/distance_enrichment.py`
- `bs3/stage1_taskset_runner.py`

## Core Stage2 Modules

- `bs3/stage2.py`
- `bs3/stage2_two_phase_scheduler.py`
- `bs3/regular_routing_common.py`
- `tools/stage2_emergency_validation_lib.py`
