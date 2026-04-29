# Stage2 Emergency Validation Summary

- suite_name: `smoke`
- scenario: `D:\Codex_Project\bs_1.0_4.22\results\stage1\normal\normal_scenario_weighted.json`
- stage1_result: `D:\Codex_Project\bs_1.0_4.22\results\stage1\static_greedy_sparsity_compare\normal_static_greedy_stop_when_feasible_result.json`
- case_count: `1`
- rho_labels: `default`

## Key Findings

- Empty-emergency degeneration: `False`
- Hotspot assessment: `insufficient_data`
- Controlled preemption used in cases: `smoke__default`
- Preemption still insufficient in cases: `smoke__default`
- Observed stage2 style: `conservative_but_stable`

## By Case Type

| case_type | count | mean_cr_emg | mean_cr_reg_before | mean_cr_reg_after | mean_preemptions | mean_elapsed_s |
|---|---:|---:|---:|---:|---:|---:|
| file_json | 1 | 0.8750 | 1.0000 | 1.0000 | 5.00 | 21.9705 |

## By Rho

| rho | count | mean_cr_emg | mean_cr_reg_after | mean_preemptions |
|---|---:|---:|---:|---:|
| default | 1 | 0.8750 | 1.0000 | 5.00 |

## Cases

| case_id | case_type | rho | emg_count | cr_emg | cr_reg_before | cr_reg_after | preemptions | degraded_reg_tasks |
|---|---|---|---:|---:|---:|---:|---:|---:|
| smoke__default | file_json | default | 8 | 0.8750 | 1.0000 | 1.0000 | 5 | 0 |
