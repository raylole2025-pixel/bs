from __future__ import annotations

import unittest

from bs3.models import (
    Allocation,
    CapacityConfig,
    CandidateWindow,
    GAConfig,
    Scenario,
    ScheduledWindow,
    Stage1BaselineTrace,
    Stage1Config,
    Stage2Config,
    Task,
)
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

    def test_emergency_direct_capacity_uses_real_time_free_cross_capacity(self) -> None:
        plan = [
            ScheduledWindow(window_id="W_slow", a="A1", b="B1", start=0.0, end=10.0, on=0.0, off=10.0),
            ScheduledWindow(window_id="W_fast", a="A1", b="B1", start=0.0, end=10.0, on=0.0, off=10.0),
        ]
        scenario = Scenario(
            node_domain={"A1": "A", "B1": "B"},
            intra_links=[],
            candidate_windows=[
                CandidateWindow(window_id="W_slow", a="A1", b="B1", start=0.0, end=10.0),
                CandidateWindow(window_id="W_fast", a="A1", b="B1", start=0.0, end=10.0),
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
                    max_rate=5.0,
                    task_type="reg",
                ),
                Task(
                    task_id="E1",
                    src="A1",
                    dst="B1",
                    arrival=0.0,
                    deadline=10.0,
                    data=50.0,
                    weight=10.0,
                    max_rate=10.0,
                    task_type="emg",
                ),
            ],
            capacities=CapacityConfig(domain_a=10.0, domain_b=10.0, cross=10.0),
            stage1=Stage1Config(
                rho=0.5,
                t_pre=0.0,
                d_min=0.0,
                theta_cap=0.0,
                theta_hot=0.0,
            ),
            stage2=Stage2Config(k_paths=2),
            planning_end=10.0,
            metadata={},
        )
        baseline_trace = Stage1BaselineTrace(
            rho=0.5,
            segments=[
                {"segment_index": 0, "start": 0.0, "end": 5.0},
                {"segment_index": 1, "start": 5.0, "end": 10.0},
            ],
            allocations=[
                Allocation(
                    task_id="R1",
                    segment_index=0,
                    path_id="R1:0:W_slow:0:0",
                    edge_ids=("W_slow",),
                    rate=5.0,
                    delivered=25.0,
                    task_type="reg",
                    cross_window_id="W_slow",
                ),
                Allocation(
                    task_id="R1",
                    segment_index=1,
                    path_id="R1:1:W_slow:0:0",
                    edge_ids=("W_slow",),
                    rate=5.0,
                    delivered=25.0,
                    task_type="reg",
                    cross_window_id="W_slow",
                ),
            ],
            completed={"R1": True},
            remaining_end={"R1": 0.0},
            cross_window_usage_by_segment={0: {"W_slow": 5.0}, 1: {"W_slow": 5.0}},
        )

        stage2_result = run_stage2(scenario, plan=plan, baseline_trace=baseline_trace)

        emergency_allocations = [alloc for alloc in stage2_result.allocations if alloc.task_id == "E1"]
        self.assertEqual(stage2_result.n_preemptions, 0)
        self.assertAlmostEqual(stage2_result.cr_emg, 1.0)
        self.assertEqual({alloc.cross_window_id for alloc in emergency_allocations}, {"W_fast"})
        self.assertEqual(stage2_result.metadata["emergency_capacity_policy"], "real_time_remaining_capacity")
        self.assertEqual(stage2_result.metadata["emergency_insertions"][0]["capacity_tier"], "direct_free")
        self.assertEqual(stage2_result.metadata["emergency_capacity_tier_counts"]["direct_free"], 1)
        self.assertNotIn(
            stage2_result.metadata["emergency_insertions"][0]["capacity_tier"],
            {"reserved_only", "borrow_unused_regular_share"},
        )


if __name__ == "__main__":
    unittest.main()
