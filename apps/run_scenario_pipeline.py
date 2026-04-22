"""Run the full Stage1 -> Stage2 pipeline on a prepared scenario JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs3.scenario import load_scenario
from bs3.pipeline import run_pipeline


def _candidate_to_dict(candidate):
    data = asdict(candidate)
    data["fr"] = candidate.fr
    data["mean_completion_ratio"] = candidate.mean_completion_ratio
    data["hotspot_coverage"] = data.get("avg_hot_coverage")
    data["hotspot_max_gap"] = data.get("max_hot_gap")
    data["plan"] = [asdict(window) for window in candidate.plan]
    return data


def _stage2_to_dict(result):
    data = asdict(result)
    data["plan"] = [asdict(window) for window in result.plan]
    data["allocations"] = [asdict(item) for item in result.allocations]
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage1 and Stage2 on a scenario JSON file.")
    parser.add_argument("scenario", help="Path to the scenario JSON file")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for Stage1 GA")
    parser.add_argument("--output", type=str, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    result = run_pipeline(scenario, seed=args.seed)
    payload = {
        "stage1": {
            "generations": result.stage1.generations,
            "selected_plan": [asdict(window) for window in result.stage1.selected_plan],
            "selected_solution": _candidate_to_dict(result.stage1.selected_solution) if result.stage1.selected_solution else None,
            "baseline_summary": dict(result.stage1.baseline_summary),
            "baseline_trace": asdict(result.stage1.baseline_trace) if result.stage1.baseline_trace is not None else None,
            "used_feedback": result.stage1.used_feedback,
            "timed_out": result.stage1.timed_out,
            "elapsed_seconds": result.stage1.elapsed_seconds,
            "stage1_screening": scenario.metadata.get("stage1_screening", {}),
        },
        "stage2_results": [_stage2_to_dict(item) for item in result.stage2_results],
        "recommended": _stage2_to_dict(result.recommended) if result.recommended is not None else None,
    }

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
