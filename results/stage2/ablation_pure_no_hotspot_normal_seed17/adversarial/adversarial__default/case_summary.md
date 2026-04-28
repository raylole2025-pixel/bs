# adversarial__default

- case_type: `file_json`
- rho: `default` -> `0.2`
- baseline_source: `stage1_result`
- emergency_count: `12`
- solver_mode: `stage2_emergency_insert`
- cr_reg_before / after: `1.0` -> `0.9533333333333334`
- cr_emg: `1.0`
- n_preemptions: `10`
- regular_completion_rate_dropped: `True`
- strict_baseline_degenerate: `False`

## Emergency Diagnostics

- direct_success_task_ids: `EMG_MIX_ADV_003, EMG_MIX_ADV_005, EMG_MIX_ADV_007, EMG_MIX_ADV_009`
- controlled_preemption_task_ids: `EMG_MIX_ADV_001, EMG_MIX_ADV_002, EMG_MIX_ADV_004, EMG_MIX_ADV_008, EMG_MIX_ADV_011, EMG_MIX_ADV_012`
- failed_task_ids: `none`
- degraded_regular_tasks: `N72X_002, N72X_029, N72X_053`
