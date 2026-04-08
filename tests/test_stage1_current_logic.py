from __future__ import annotations

import unittest

from bs3.models import CapacityConfig, CandidateWindow, GAConfig, HotspotRegion, Scenario, Stage1Config, Stage2Config, Task, TemporalLink
from bs3.stage1 import run_stage1
from bs3.stage1_static_value import compute_candidate_static_values


class Stage1CurrentLogicTests(unittest.TestCase):
    def test_static_value_uses_hop_reachability_pressure(self) -> None:
        scenario = Scenario(
            node_domain={"A1": "A", "A2": "A", "B1": "B", "B2": "B"},
            intra_links=[],
            candidate_windows=[
                CandidateWindow(window_id="W1", a="A1", b="B1", start=0.0, end=20.0),
                CandidateWindow(window_id="W2", a="A2", b="B2", start=0.0, end=20.0),
            ],
            tasks=[
                Task(
                    task_id="T1",
                    src="A1",
                    dst="B1",
                    arrival=0.0,
                    deadline=20.0,
                    data=100.0,
                    weight=1.0,
                    max_rate=10.0,
                    task_type="reg",
                )
            ],
            capacities=CapacityConfig(domain_a=10.0, domain_b=10.0, cross=10.0),
            stage1=Stage1Config(rho=0.0, t_pre=0.0, d_min=0.0),
            stage2=Stage2Config(),
            planning_end=20.0,
            metadata={},
        )
        scenario.intra_links = [
            # A1/A2 and B1/B2 each differ by one hop.
            TemporalLink("LA", "A1", "A2", "A", 0.0, 20.0),
            TemporalLink("LB", "B1", "B2", "B", 0.0, 20.0),
        ]

        values = compute_candidate_static_values(scenario, snapshot_seconds=20)

        self.assertGreater(values["W1"], values["W2"])

    def test_stage1_returns_feasible_single_window_plan(self) -> None:
        scenario = Scenario(
            node_domain={"A1": "A", "B1": "B"},
            intra_links=[],
            candidate_windows=[
                CandidateWindow(window_id="W1", a="A1", b="B1", start=0.0, end=10.0),
            ],
            tasks=[
                Task(
                    task_id="T1",
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
                theta_sr=1.0,
                theta_cap=0.0,
                theta_hot=0.0,
                q_eval=1,
                elite_prune_count=0,
                ga=GAConfig(population_size=4, max_generations=3, stall_generations=1, top_m=1),
            ),
            stage2=Stage2Config(),
            planning_end=10.0,
            metadata={},
        )

        result = run_stage1(scenario, seed=1)

        self.assertTrue(result.best_feasible)
        best = result.best_feasible[0]
        self.assertTrue(best.feasible)
        self.assertEqual(best.window_count, 1)
        self.assertEqual(best.activation_count, 2)
        self.assertAlmostEqual(best.mean_completion_ratio, 1.0)
        self.assertAlmostEqual(best.full_success_rate, 1.0)
        self.assertAlmostEqual(best.sr_theta_c, 1.0)
        self.assertAlmostEqual(best.hotspot_coverage, 1.0)
        self.assertEqual(len(best.fitness), 4)
        self.assertFalse(hasattr(best, "f_reg"))

    def test_stage1_hotspot_coverage_remains_formal_feasibility_constraint(self) -> None:
        scenario = Scenario(
            node_domain={"A1": "A", "A2": "A", "B1": "B"},
            intra_links=[
                TemporalLink("LA", "A1", "A2", "A", 0.0, 10.0),
            ],
            candidate_windows=[
                CandidateWindow(window_id="W1", a="A1", b="B1", start=0.0, end=10.0),
            ],
            tasks=[
                Task(
                    task_id="T1",
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
                theta_sr=1.0,
                theta_cap=0.0,
                theta_hot=1.0,
                hot_hop_limit=0,
                q_eval=1,
                elite_prune_count=0,
                ga=GAConfig(population_size=4, max_generations=3, stall_generations=1, top_m=1),
            ),
            stage2=Stage2Config(),
            planning_end=10.0,
            hotspots_a=[HotspotRegion(region_id="H1", weight=1.0, nodes=("A2",))],
            metadata={},
        )

        result = run_stage1(scenario, seed=1)

        self.assertFalse(result.best_feasible)
        self.assertIsNotNone(result.population_best)
        self.assertAlmostEqual(result.population_best.hotspot_coverage, 0.0)
        self.assertGreater(result.population_best.violation, 0.0)
        self.assertEqual(len(result.population_best.fitness), 6)

    def test_stage1_requires_true_full_completion_for_feasibility(self) -> None:
        scenario = Scenario(
            node_domain={"A1": "A", "B1": "B"},
            intra_links=[],
            candidate_windows=[
                CandidateWindow(window_id="W1", a="A1", b="B1", start=0.0, end=9.5),
            ],
            tasks=[
                Task(
                    task_id="T1",
                    src="A1",
                    dst="B1",
                    arrival=0.0,
                    deadline=10.0,
                    data=100.0,
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
                theta_sr=1.0,
                theta_cap=0.0,
                theta_hot=0.0,
                q_eval=1,
                elite_prune_count=0,
                ga=GAConfig(population_size=4, max_generations=3, stall_generations=1, top_m=1),
            ),
            stage2=Stage2Config(),
            planning_end=10.0,
            metadata={},
        )

        result = run_stage1(scenario, seed=1)

        self.assertFalse(result.best_feasible)
        self.assertIsNotNone(result.population_best)
        self.assertAlmostEqual(result.population_best.mean_completion_ratio, 0.95)
        self.assertAlmostEqual(result.population_best.full_success_rate, 0.0)
        self.assertGreater(result.population_best.violation, 0.0)


if __name__ == "__main__":
    unittest.main()
