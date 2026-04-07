from __future__ import annotations

import copy
import unittest

from bs3.models import (
    CandidateWindow,
    CapacityConfig,
    GAConfig,
    Scenario,
    ScheduledWindow,
    Stage1Config,
    Stage2Config,
    Task,
    TemporalLink,
)
from bs3.scenario import validate_scenario
from bs3.stage2 import run_stage2


BASE_PAYLOAD = {
    "metadata": {"name": "stage2-baseline-insert-test"},
    "planning_end": 6.0,
    "nodes": {
        "A": ["A1", "A2"],
        "B": ["B1", "B2"],
    },
    "capacities": {"A": 10.0, "B": 10.0, "X": 10.0},
    "stage1": {
        "rho": 0.2,
        "t_pre": 1.0,
        "d_min": 1.0,
    },
    "stage2": {
        "k_paths": 2,
        "completion_tolerance": 1e-6,
    },
    "intra_domain_links": [
        {"id": "A12", "u": "A1", "v": "A2", "domain": "A", "start": 0.0, "end": 6.0, "delay": 0.1},
        {"id": "B12", "u": "B1", "v": "B2", "domain": "B", "start": 0.0, "end": 6.0, "delay": 0.1},
    ],
    "candidate_windows": [
        {"id": "X1", "a": "A1", "b": "B1", "start": 0.0, "end": 6.0, "delay": 0.1},
        {"id": "X2", "a": "A2", "b": "B2", "start": 0.0, "end": 6.0, "delay": 0.1},
    ],
    "tasks": [],
}

PLAN = [
    ScheduledWindow(window_id="X1", a="A1", b="B1", start=0.0, end=6.0, on=0.0, off=6.0, delay=0.1),
    ScheduledWindow(window_id="X2", a="A2", b="B2", start=0.0, end=6.0, on=0.0, off=6.0, delay=0.1),
]


def _load_payload(payload: dict) -> Scenario:
    scenario = Scenario(
        node_domain={
            **{node: "A" for node in payload["nodes"]["A"]},
            **{node: "B" for node in payload["nodes"]["B"]},
        },
        intra_links=[
            TemporalLink(
                link_id=item["id"],
                u=item["u"],
                v=item["v"],
                domain=item["domain"],
                start=float(item["start"]),
                end=float(item["end"]),
                delay=float(item.get("delay", 0.0)),
                weight=float(item.get("weight", item.get("delay", 1.0) or 1.0)),
            )
            for item in payload["intra_domain_links"]
        ],
        candidate_windows=[
            CandidateWindow(
                window_id=item["id"],
                a=item["a"],
                b=item["b"],
                start=float(item["start"]),
                end=float(item["end"]),
                value=item.get("value"),
                delay=float(item.get("delay", 0.0)),
            )
            for item in payload["candidate_windows"]
        ],
        tasks=[
            Task(
                task_id=item["id"],
                src=item["src"],
                dst=item["dst"],
                arrival=float(item["arrival"]),
                deadline=float(item["deadline"]),
                data=float(item["data"]),
                weight=float(item["weight"]),
                max_rate=float(item["max_rate"]),
                task_type=item["type"],
                preemption_priority=float(item.get("preemption_priority", item["weight"])),
            )
            for item in payload["tasks"]
        ],
        capacities=CapacityConfig(
            domain_a=float(payload["capacities"]["A"]),
            domain_b=float(payload["capacities"]["B"]),
            cross=float(payload["capacities"]["X"]),
        ),
        stage1=Stage1Config(
            rho=float(payload["stage1"]["rho"]),
            t_pre=float(payload["stage1"]["t_pre"]),
            d_min=float(payload["stage1"]["d_min"]),
            ga=GAConfig(),
        ),
        stage2=Stage2Config(
            k_paths=int(payload["stage2"]["k_paths"]),
            completion_tolerance=float(payload["stage2"]["completion_tolerance"]),
        ),
        planning_end=float(payload["planning_end"]),
        metadata=copy.deepcopy(payload.get("metadata", {})),
    )
    validate_scenario(scenario)
    return scenario


def _task_allocation(result, task_id: str):
    return [alloc for alloc in result.allocations if alloc.task_id == task_id]


class Stage2BaselineInsertTests(unittest.TestCase):
    def test_stage2_reports_fixed_mode(self) -> None:
        payload = copy.deepcopy(BASE_PAYLOAD)
        payload["tasks"] = [
            {
                "id": "R1",
                "src": "A1",
                "dst": "B1",
                "arrival": 0.0,
                "deadline": 4.0,
                "data": 4.0,
                "weight": 1.0,
                "max_rate": 2.0,
                "type": "reg",
            }
        ]
        scenario = _load_payload(payload)
        result = run_stage2(scenario, PLAN)
        self.assertEqual(result.solver_mode, "two_phase_event_insert")

    def test_regular_baseline_uses_only_reserved_cross_slice(self) -> None:
        payload = copy.deepcopy(BASE_PAYLOAD)
        payload["tasks"] = [
            {
                "id": "R1",
                "src": "A1",
                "dst": "B1",
                "arrival": 0.0,
                "deadline": 2.0,
                "data": 20.0,
                "weight": 3.0,
                "max_rate": 10.0,
                "type": "reg",
            }
        ]
        scenario = _load_payload(payload)
        result = run_stage2(scenario, PLAN)
        allocations = _task_allocation(result, "R1")
        self.assertTrue(allocations)
        reserved_cross = (1.0 - scenario.stage1.rho) * scenario.capacities.cross
        self.assertTrue(all(alloc.rate <= reserved_cross + 1e-9 for alloc in allocations))
        self.assertLess(result.cr_reg, 1.0)

    def test_direct_insert_uses_reserved_capacity_without_preemption(self) -> None:
        payload = copy.deepcopy(BASE_PAYLOAD)
        payload["tasks"] = [
            {
                "id": "R1",
                "src": "A1",
                "dst": "B1",
                "arrival": 0.0,
                "deadline": 3.0,
                "data": 15.0,
                "weight": 1.0,
                "max_rate": 5.0,
                "type": "reg",
            },
            {
                "id": "E1",
                "src": "A2",
                "dst": "B2",
                "arrival": 0.0,
                "deadline": 3.0,
                "data": 12.0,
                "weight": 5.0,
                "max_rate": 5.0,
                "type": "emg",
            },
        ]
        scenario = _load_payload(payload)
        result = run_stage2(scenario, PLAN)
        self.assertEqual(result.n_preemptions, 0)
        self.assertEqual(result.cr_emg, 1.0)
        self.assertTrue(_task_allocation(result, "R1"))
        self.assertTrue(_task_allocation(result, "E1"))

    def test_emergency_arrival_uses_split_segment_immediately(self) -> None:
        payload = copy.deepcopy(BASE_PAYLOAD)
        payload["planning_end"] = 4.0
        payload["tasks"] = [
            {
                "id": "E1",
                "src": "A1",
                "dst": "B1",
                "arrival": 1.5,
                "deadline": 3.5,
                "data": 2.0,
                "weight": 5.0,
                "max_rate": 2.0,
                "type": "emg",
            }
        ]
        scenario = _load_payload(payload)
        result = run_stage2(scenario, PLAN)
        allocations = _task_allocation(result, "E1")
        self.assertTrue(allocations)
        self.assertEqual(allocations[0].segment_index, 1)

    def test_controlled_preemption_releases_low_weight_regular_task(self) -> None:
        payload = copy.deepcopy(BASE_PAYLOAD)
        payload["planning_end"] = 4.0
        payload["capacities"] = {"A": 8.0, "B": 8.0, "X": 8.0}
        payload["candidate_windows"] = [
            {"id": "X1", "a": "A1", "b": "B1", "start": 0.0, "end": 4.0, "delay": 0.0}
        ]
        payload["tasks"] = [
            {
                "id": "R_hi",
                "src": "A1",
                "dst": "B1",
                "arrival": 0.0,
                "deadline": 2.0,
                "data": 8.0,
                "weight": 5.0,
                "max_rate": 4.0,
                "type": "reg",
            },
            {
                "id": "R_lo",
                "src": "A1",
                "dst": "B1",
                "arrival": 0.0,
                "deadline": 4.0,
                "data": 8.0,
                "weight": 1.0,
                "max_rate": 4.0,
                "type": "reg",
            },
            {
                "id": "E1",
                "src": "A1",
                "dst": "B1",
                "arrival": 1.0,
                "deadline": 3.0,
                "data": 12.0,
                "weight": 10.0,
                "max_rate": 8.0,
                "type": "emg",
            },
        ]
        scenario = _load_payload(payload)
        local_plan = [
            ScheduledWindow(window_id="X1", a="A1", b="B1", start=0.0, end=4.0, on=0.0, off=4.0, delay=0.0)
        ]
        result = run_stage2(scenario, local_plan)
        delivered = {task_id: sum(alloc.delivered for alloc in _task_allocation(result, task_id)) for task_id in ("R_hi", "R_lo", "E1")}
        self.assertGreaterEqual(result.n_preemptions, 1)
        self.assertAlmostEqual(delivered["E1"], 12.0, delta=1e-6)
        self.assertGreater(delivered["R_hi"], delivered["R_lo"])

    def test_legacy_insertion_horizon_is_ignored_and_deadline_horizon_is_used(self) -> None:
        payload = copy.deepcopy(BASE_PAYLOAD)
        payload["planning_end"] = 5.0
        payload["stage2"]["insertion_horizon_seconds"] = 0.5
        payload["tasks"] = [
            {
                "id": "E1",
                "src": "A1",
                "dst": "B1",
                "arrival": 1.0,
                "deadline": 4.0,
                "data": 6.0,
                "weight": 5.0,
                "max_rate": 2.0,
                "type": "emg",
            }
        ]
        scenario = _load_payload(payload)
        result = run_stage2(scenario, PLAN)
        delivered = sum(alloc.delivered for alloc in _task_allocation(result, "E1"))
        self.assertAlmostEqual(delivered, 6.0, delta=1e-6)
        self.assertEqual(result.cr_emg, 1.0)

    def test_best_effort_commits_partial_emergency_flow_on_failure(self) -> None:
        payload = copy.deepcopy(BASE_PAYLOAD)
        payload["planning_end"] = 3.0
        payload["tasks"] = [
            {
                "id": "E1",
                "src": "A1",
                "dst": "B1",
                "arrival": 0.0,
                "deadline": 3.0,
                "data": 40.0,
                "weight": 5.0,
                "max_rate": 10.0,
                "type": "emg",
            }
        ]
        scenario = _load_payload(payload)
        result = run_stage2(scenario, PLAN)
        delivered = sum(alloc.delivered for alloc in _task_allocation(result, "E1"))
        self.assertGreater(delivered, 0.0)
        self.assertLess(delivered, 40.0)
        self.assertEqual(result.cr_emg, 0.0)


if __name__ == "__main__":
    unittest.main()


