# smoke__default

- case_type: `file_json`
- rho: `default` -> `0.2`
- baseline_source: `stage1_result`
- emergency_count: `8`
- solver_mode: `stage2_emergency_insert`
- cr_reg_before / after: `1.0` -> `0.9866666666666667`
- cr_emg: `0.875`
- n_preemptions: `5`
- regular_completion_rate_dropped: `True`
- strict_baseline_degenerate: `False`

## Emergency Diagnostics

- direct_success_task_ids: `EMG_MIX_SMO_001, EMG_MIX_SMO_003, EMG_MIX_SMO_004, EMG_MIX_SMO_006`
- controlled_preemption_task_ids: `EMG_MIX_SMO_002`
- failed_task_ids: `EMG_MIX_SMO_008`
- degraded_regular_tasks: `N72X_029`
