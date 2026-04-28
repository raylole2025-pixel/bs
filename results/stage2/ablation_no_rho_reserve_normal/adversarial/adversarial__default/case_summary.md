# adversarial__default

- case_type: `file_json`
- rho: `default` -> `0.0`
- baseline_source: `stage1_result`
- emergency_count: `12`
- solver_mode: `stage2_emergency_insert`
- cr_reg_before / after: `1.0` -> `0.8266666666666667`
- cr_emg: `0.8333333333333334`
- n_preemptions: `13`
- regular_completion_rate_dropped: `True`
- strict_baseline_degenerate: `False`

## Emergency Diagnostics

- direct_success_task_ids: `none`
- controlled_preemption_task_ids: `EMG_MIX_ADV_001, EMG_MIX_ADV_002, EMG_MIX_ADV_003, EMG_MIX_ADV_004, EMG_MIX_ADV_005, EMG_MIX_ADV_007, EMG_MIX_ADV_009, EMG_MIX_ADV_010, EMG_MIX_ADV_011`
- failed_task_ids: `EMG_MIX_ADV_006, EMG_MIX_ADV_012`
- degraded_regular_tasks: `N72X_013, N72X_015, N72X_027, N72X_030, N72X_039, N72X_040, N72X_042, N72X_051, N72X_053, N72X_063`
