from __future__ import annotations

import unittest

from bs3.models import CapacityConfig, CandidateWindow, GAConfig, Scenario, Stage1Config, Task
from bs3.stage1 import run_stage1
from bs3.stage2 import run_stage2


class Stage2PipelineSmokeTests(unittest.TestCase):
    def test_stage2_degenerates_to_stage1_baseline_without_emergencies(self) -> None:
        scenario = Scenario(
            node_domain={"A1": "A", "B1": "B"},
            intra_links=[],
            candidate_windows=[
                CandidateWindow(window_id="W1", a="A1", b="B1", start=0.0, end=10.0),
            ],
            tasks=[
                Task(
                    task_id="R1",
                    src="A1",
                    dst="B1",
                    arrival=0.0,
                    deadline=10.0,
                    data=50.0,
                    weight=1.0,
                    max_rate=10.0,
                    task_type="reg",
                )
            ],
            capacities=CapacityConfig(domain_a=10.0, domain_b=10.0, cross=10.0),
            stage1=Stage1Config(
                rho=0.0,
                t_pre=0.0,
                d_min=0.0,
                theta_cap=0.0,
                theta_hot=0.0,
                q_eval=1,
                elite_prune_count=0,
                ga=GAConfig(population_size=4, max_generations=3, stall_generations=1, top_m=1),
            ),
            planning_end=10.0,
            metadata={},
        )

        stage1_result = run_stage1(scenario, seed=1)
        self.assertTrue(stage1_result.selected_plan)
        self.assertIsNotNone(stage1_result.baseline_trace)

        stage2_result = run_stage2(scenario, stage1_result=stage1_result)

        self.assertEqual(len(stage2_result.plan), len(stage1_result.selected_plan))
        self.assertEqual(stage2_result.n_preemptions, 0)
        self.assertAlmostEqual(stage2_result.cr_reg, 1.0)
        self.assertEqual(stage2_result.solver_mode, "stage2_emergency_insert")
        self.assertTrue(stage2_result.allocations)


if __name__ == "__main__":
    unittest.main()
