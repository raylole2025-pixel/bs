# stress__default

- case_type: `file_json`
- rho: `default` -> `0.0`
- baseline_source: `stage1_result`
- emergency_count: `20`
- solver_mode: `stage2_emergency_insert`
- cr_reg_before / after: `1.0` -> `0.7866666666666666`
- cr_emg: `0.75`
- n_preemptions: `21`
- regular_completion_rate_dropped: `True`
- strict_baseline_degenerate: `False`

## Emergency Diagnostics

- direct_success_task_ids: `EMG_MIX_STR_019`
- controlled_preemption_task_ids: `EMG_MIX_STR_001, EMG_MIX_STR_002, EMG_MIX_STR_005, EMG_MIX_STR_006, EMG_MIX_STR_008, EMG_MIX_STR_011, EMG_MIX_STR_012, EMG_MIX_STR_013, EMG_MIX_STR_015, EMG_MIX_STR_016, EMG_MIX_STR_017`
- failed_task_ids: `EMG_MIX_STR_003, EMG_MIX_STR_004, EMG_MIX_STR_010, EMG_MIX_STR_018, EMG_MIX_STR_020`
- degraded_regular_tasks: `N72X_004, N72X_025, N72X_026, N72X_027, N72X_028, N72X_029, N72X_030, N72X_050, N72X_052, N72X_053, N72X_054, N72X_055, N72X_064, N72X_065`
