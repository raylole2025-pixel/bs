# Stage2 Emergency Validation Summary

- suite_name: `stress`
- scenario: `D:\Codex_Project\bs_1.0_4.22\results\stage1\ablation_no_rho_reserve_normal\normal_tasks_20260428_113942\normal_tasks_scenario_annotated.json`
- stage1_result: `D:\Codex_Project\bs_1.0_4.22\results\stage1\ablation_no_rho_reserve_normal\normal_tasks_20260428_113942\normal_tasks_stage1_result.json`
- case_count: `1`
- rho_labels: `default`

## Key Findings

- Empty-emergency degeneration: `False`
- Hotspot assessment: `insufficient_data`
- Controlled preemption used in cases: `stress__default`
- Preemption still insufficient in cases: `stress__default`
- Observed stage2 style: `balanced_tradeoff`

## By Case Type

| case_type | count | mean_cr_emg | mean_cr_reg_before | mean_cr_reg_after | mean_preemptions | mean_elapsed_s |
|---|---:|---:|---:|---:|---:|---:|
| file_json | 1 | 0.7500 | 1.0000 | 0.7867 | 21.00 | 72.1227 |

## By Rho

| rho | count | mean_cr_emg | mean_cr_reg_after | mean_preemptions |
|---|---:|---:|---:|---:|
| default | 1 | 0.7500 | 0.7867 | 21.00 |

## Cases

| case_id | case_type | rho | emg_count | cr_emg | cr_reg_before | cr_reg_after | preemptions | degraded_reg_tasks |
|---|---|---|---:|---:|---:|---:|---:|---:|
| stress__default | file_json | default | 20 | 0.7500 | 1.0000 | 0.7867 | 21 | 14 |
