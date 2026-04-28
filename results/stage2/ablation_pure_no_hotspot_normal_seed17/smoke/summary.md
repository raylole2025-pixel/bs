# Stage2 Emergency Validation Summary

- suite_name: `smoke`
- scenario: `D:\Codex_Project\bs_1.0_4.22\results\stage1\ablation_pure_no_hotspot_normal_seed17\normal_tasks_20260428_092126\normal_tasks_scenario_annotated.json`
- stage1_result: `D:\Codex_Project\bs_1.0_4.22\results\stage1\ablation_pure_no_hotspot_normal_seed17\normal_tasks_20260428_092126\normal_tasks_stage1_result.json`
- case_count: `1`
- rho_labels: `default`

## Key Findings

- Empty-emergency degeneration: `False`
- Hotspot assessment: `insufficient_data`
- Controlled preemption used in cases: `smoke__default`
- Preemption still insufficient in cases: `smoke__default`
- Observed stage2 style: `balanced_tradeoff`

## By Case Type

| case_type | count | mean_cr_emg | mean_cr_reg_before | mean_cr_reg_after | mean_preemptions | mean_elapsed_s |
|---|---:|---:|---:|---:|---:|---:|
| file_json | 1 | 0.8750 | 1.0000 | 0.9867 | 5.00 | 18.8163 |

## By Rho

| rho | count | mean_cr_emg | mean_cr_reg_after | mean_preemptions |
|---|---:|---:|---:|---:|
| default | 1 | 0.8750 | 0.9867 | 5.00 |

## Cases

| case_id | case_type | rho | emg_count | cr_emg | cr_reg_before | cr_reg_after | preemptions | degraded_reg_tasks |
|---|---|---|---:|---:|---:|---:|---:|---:|
| smoke__default | file_json | default | 8 | 0.8750 | 1.0000 | 0.9867 | 5 | 1 |
