# Stage2 Emergency Validation Summary

- suite_name: `adversarial`
- scenario: `D:\Codex_Project\bs_1.0_4.22\results\stage1\normal\normal_scenario_annotated.json`
- stage1_result: `D:\Codex_Project\bs_1.0_4.22\results\stage1\normal\normal_stage1_result.json`
- case_count: `1`
- rho_labels: `default`

## Key Findings

- Empty-emergency degeneration: `False`
- Hotspot assessment: `insufficient_data`
- Controlled preemption used in cases: `adversarial__default`
- Preemption still insufficient in cases: `adversarial__default`
- Observed stage2 style: `aggressive_but_regular_damage_visible`

## By Case Type

| case_type | count | mean_cr_emg | mean_cr_reg_before | mean_cr_reg_after | mean_preemptions | mean_elapsed_s |
|---|---:|---:|---:|---:|---:|---:|
| file_json | 1 | 0.9167 | 1.0000 | 0.9533 | 11.00 | 53.7133 |

## By Rho

| rho | count | mean_cr_emg | mean_cr_reg_after | mean_preemptions |
|---|---:|---:|---:|---:|
| default | 1 | 0.9167 | 0.9533 | 11.00 |

## Cases

| case_id | case_type | rho | emg_count | cr_emg | cr_reg_before | cr_reg_after | preemptions | degraded_reg_tasks |
|---|---|---|---:|---:|---:|---:|---:|---:|
| adversarial__default | file_json | default | 12 | 0.9167 | 1.0000 | 0.9533 | 11 | 3 |
