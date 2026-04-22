from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bs3.stage1_taskset_runner import Stage1TasksetRunConfig, run_stage1_on_taskset_json


class Stage1JsonTasksetRunnerTests(unittest.TestCase):
    def test_json_taskset_runner_produces_stage1_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            base_scenario = tmpdir / "base_scenario.json"
            taskset_json = tmpdir / "tasks.json"
            output_root = tmpdir / "outputs"

            base_payload = {
                "metadata": {"name": "unit-test-scenario"},
                "planning_end": 10.0,
                "nodes": {"A": ["A1"], "B": ["B1"]},
                "capacities": {"A": 10.0, "B": 10.0, "X": 10.0},
                "stage1": {
                    "rho": 0.0,
                    "t_pre": 0.0,
                    "d_min": 0.0,
                    "theta_cap": 0.0,
                    "theta_hot": 0.0,
                    "q_eval": 1,
                    "elite_prune_count": 0,
                    "ga": {
                        "population_size": 4,
                        "max_generations": 3,
                        "stall_generations": 1,
                        "top_m": 1,
                    },
                },
                "intra_domain_links": [],
                "candidate_windows": [
                    {"id": "W1", "a": "A1", "b": "B1", "start": 0.0, "end": 10.0, "value": None},
                ],
                "tasks": [],
            }
            tasks_payload = [
                {
                    "id": "T1",
                    "src": "A1",
                    "dst": "B1",
                    "arrival": 0.0,
                    "deadline": 10.0,
                    "data": 50.0,
                    "weight": 1.0,
                    "max_rate": 10.0,
                    "type": "reg",
                    "preemption_priority": 1.0,
                }
            ]

            base_scenario.write_text(json.dumps(base_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            taskset_json.write_text(json.dumps(tasks_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            summary = run_stage1_on_taskset_json(
                taskset_json,
                base_scenario_path=base_scenario,
                output_root=output_root,
                config=Stage1TasksetRunConfig(
                    seed=1,
                    disable_distance_enrichment=True,
                    export_artifacts=False,
                    theta_cap=0.0,
                    theta_hot=0.0,
                    rho=0.0,
                    t_pre=0.0,
                    d_min=0.0,
                    q_eval=1,
                    elite_prune_count=0,
                    population_size=4,
                    max_generations=3,
                    stall_generations=1,
                    top_m=1,
                ),
            )

            result_file = Path(summary["result_file"])
            self.assertTrue(result_file.exists())
            result_payload = json.loads(result_file.read_text(encoding="utf-8"))
            self.assertTrue(result_payload["selected_plan"])
            self.assertIsNotNone(result_payload["selected_solution"])
            self.assertEqual(result_payload["selected_solution"]["window_count"], 1)
            self.assertIsNotNone(result_payload["baseline_trace_file"])
            baseline_trace_file = result_file.parent / str(result_payload["baseline_trace_file"])
            self.assertTrue(baseline_trace_file.exists())


if __name__ == "__main__":
    unittest.main()
