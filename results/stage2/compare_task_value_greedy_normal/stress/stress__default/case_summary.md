# stress__default

- case_type: `file_json`
- rho: `default` -> `0.2`
- baseline_source: `stage1_result`
- emergency_count: `20`
- solver_mode: `stage2_emergency_insert`
- cr_reg_before / after: `1.0` -> `0.86`
- cr_emg: `0.8`
- n_preemptions: `20`
- regular_completion_rate_dropped: `True`
- strict_baseline_degenerate: `False`

## Emergency Diagnostics

- direct_success_task_ids: `EMG_MIX_STR_011, EMG_MIX_STR_019`
- controlled_preemption_task_ids: `EMG_MIX_STR_001, EMG_MIX_STR_002, EMG_MIX_STR_004, EMG_MIX_STR_005, EMG_MIX_STR_006, EMG_MIX_STR_009, EMG_MIX_STR_012, EMG_MIX_STR_013, EMG_MIX_STR_016, EMG_MIX_STR_017, EMG_MIX_STR_018`
- failed_task_ids: `EMG_MIX_STR_003, EMG_MIX_STR_008, EMG_MIX_STR_010, EMG_MIX_STR_020`
- degraded_regular_tasks: `N72X_001, N72X_006, N72X_025, N72X_027, N72X_028, N72X_030, N72X_031, N72X_032, N72X_054, N72X_056`
