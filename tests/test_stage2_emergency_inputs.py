from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.stage2_emergency_validation_lib import build_stage2_effective_payload, load_emergency_tasks_from_json


class Stage2EmergencyInputTests(unittest.TestCase):
    def test_mixed_json_extracts_only_emergencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_json = Path(tmp) / "mixed_tasks.json"
            task_json.write_text(
                json.dumps(
                    [
                        {
                            "id": "R1",
                            "src": "A1",
                            "dst": "B1",
                            "arrival": 0.0,
                            "deadline": 10.0,
                            "data": 50.0,
                            "weight": 1.0,
                            "max_rate": 10.0,
                            "type": "reg",
                        },
                        {
                            "id": "E1",
                            "src": "A1",
                            "dst": "B1",
                            "arrival": 1.0,
                            "deadline": 5.0,
                            "data": 20.0,
                            "weight": 5.0,
                            "max_rate": 10.0,
                            "type": "emg",
                            "preemption_priority": 10.0,
                        },
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            tasks = load_emergency_tasks_from_json(task_json)

            self.assertEqual([task["id"] for task in tasks], ["E1"])
            self.assertTrue(all(task["type"] == "emg" for task in tasks))

    def test_effective_payload_keeps_base_regular_tasks(self) -> None:
        base_payload = {
            "metadata": {"name": "base"},
            "tasks": [
                {
                    "id": "R1",
                    "src": "A1",
                    "dst": "B1",
                    "arrival": 0.0,
                    "deadline": 10.0,
                    "data": 50.0,
                    "weight": 1.0,
                    "max_rate": 10.0,
                    "type": "reg",
                }
            ],
        }
        emergency_tasks = [
            {
                "id": "E1",
                "src": "A1",
                "dst": "B1",
                "arrival": 1.0,
                "deadline": 5.0,
                "data": 20.0,
                "weight": 5.0,
                "max_rate": 10.0,
                "type": "emg",
                "preemption_priority": 10.0,
            }
        ]

        payload = build_stage2_effective_payload(
            base_payload=base_payload,
            emergency_tasks=emergency_tasks,
            metadata_updates={"runner": "unit-test"},
        )

        self.assertEqual([task["id"] for task in payload["tasks"]], ["R1", "E1"])
        self.assertEqual(payload["metadata"]["runner"], "unit-test")


if __name__ == "__main__":
    unittest.main()
