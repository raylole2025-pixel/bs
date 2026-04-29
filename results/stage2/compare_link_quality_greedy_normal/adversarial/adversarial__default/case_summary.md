# adversarial__default

- case_type: `file_json`
- rho: `default` -> `0.2`
- baseline_source: `stage1_result`
- emergency_count: `12`
- solver_mode: `stage2_emergency_insert`
- cr_reg_before / after: `0.5866666666666667` -> `0.5266666666666666`
- cr_emg: `0.75`
- n_preemptions: `8`
- regular_completion_rate_dropped: `True`
- strict_baseline_degenerate: `False`

## Emergency Diagnostics

- direct_success_task_ids: `EMG_MIX_ADV_001, EMG_MIX_ADV_002, EMG_MIX_ADV_003, EMG_MIX_ADV_004`
- controlled_preemption_task_ids: `EMG_MIX_ADV_007, EMG_MIX_ADV_009, EMG_MIX_ADV_011`
- failed_task_ids: `EMG_MIX_ADV_005, EMG_MIX_ADV_006, EMG_MIX_ADV_010`
- degraded_regular_tasks: `N72X_037, N72X_039, N72X_051`
