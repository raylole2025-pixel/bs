from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

from .models import CandidateWindow, Scenario
from .scenario import build_domain_graph

EPS = 1e-9


@dataclass(frozen=True)
class StaticValueSegment:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def _static_value_segments(scenario: Scenario, snapshot_seconds: int) -> list[StaticValueSegment]:
    step = max(int(snapshot_seconds), 1)
    times = {0.0, float(scenario.planning_end)}

    for task in scenario.tasks:
        if task.task_type != "reg":
            continue
        times.add(float(task.arrival))
        times.add(float(task.deadline))

    current = 0.0
    while current < scenario.planning_end - EPS:
        times.add(current)
        current = min(scenario.planning_end, current + step)
    times.add(float(scenario.planning_end))

    ordered = sorted(value for value in times if 0.0 <= value <= scenario.planning_end)
    return [
        StaticValueSegment(start=start, end=end)
        for start, end in zip(ordered, ordered[1:])
        if end > start + EPS
    ]


def _hop_lengths(graph: nx.Graph, sources: set[str]) -> dict[str, dict[str, int]]:
    results: dict[str, dict[str, int]] = {}
    for source in sources:
        if source not in graph:
            results[source] = {}
            continue
        results[source] = dict(nx.single_source_shortest_path_length(graph, source))
    return results


def compute_candidate_static_values(
    scenario: Scenario,
    snapshot_seconds: int | None = None,
) -> dict[str, float]:
    regular_tasks = [
        task
        for task in scenario.tasks
        if task.task_type == "reg" and scenario.node_domain[task.src] != scenario.node_domain[task.dst]
    ]
    values = {window.window_id: 0.0 for window in scenario.candidate_windows}
    if not regular_tasks or not scenario.candidate_windows:
        scenario.metadata.setdefault("stage1_static_value", {})
        scenario.metadata["stage1_static_value"]["mode"] = "not_used"
        return values

    snapshot_seconds = (
        scenario.stage1.static_value_snapshot_seconds if snapshot_seconds is None else snapshot_seconds
    )
    segments = _static_value_segments(scenario, snapshot_seconds)
    scenario.metadata.setdefault("stage1_static_value", {})
    scenario.metadata["stage1_static_value"].update(
        {
            "mode": "hop_reachability_pressure",
            "snapshot_seconds": snapshot_seconds,
            "segment_count": len(segments),
        }
    )

    for segment in segments:
        active_windows = [
            window
            for window in scenario.candidate_windows
            if window.start < segment.end and window.end > segment.start
        ]
        if not active_windows:
            continue

        active_tasks = [
            task
            for task in regular_tasks
            if task.arrival <= segment.start < task.deadline
        ]
        if not active_tasks:
            continue

        graph_a = build_domain_graph(scenario, "A", segment.start)
        graph_b = build_domain_graph(scenario, "B", segment.start)
        gateways_a = {window.a for window in active_windows}
        gateways_b = {window.b for window in active_windows}
        sources_a = {task.src for task in active_tasks if scenario.node_domain[task.src] == "A"} | gateways_a
        sources_b = {task.dst for task in active_tasks if scenario.node_domain[task.dst] == "B"} | gateways_b
        hop_from_a = _hop_lengths(graph_a, sources_a)
        hop_from_b = _hop_lengths(graph_b, sources_b)

        pair_pressure: dict[tuple[str, str], float] = defaultdict(float)
        for task in active_tasks:
            demand = min(task.max_rate, task.data / max(task.deadline - segment.start, EPS))
            if demand <= EPS:
                continue
            task_weight = task.weight * demand
            src_hops = hop_from_a.get(task.src, {})
            dst_hops = hop_from_b.get(task.dst, {})
            for window in active_windows:
                hop_a = src_hops.get(window.a)
                hop_b = dst_hops.get(window.b)
                if hop_a is None or hop_b is None:
                    continue
                accessibility = 1.0 / (1.0 + float(hop_a) + float(hop_b))
                pair_pressure[(window.a, window.b)] += task_weight * accessibility

        if not pair_pressure:
            continue

        for window in active_windows:
            overlap = max(0.0, min(window.end, segment.end) - max(window.start, segment.start))
            if overlap <= EPS:
                continue
            values[window.window_id] += overlap * pair_pressure.get((window.a, window.b), 0.0)

    return values


def annotate_scenario_candidate_values(
    scenario: Scenario,
    snapshot_seconds: int | None = None,
    force: bool = False,
) -> dict[str, float]:
    if not force and scenario.candidate_windows and all(window.value is not None for window in scenario.candidate_windows):
        return {window.window_id: float(window.value or 0.0) for window in scenario.candidate_windows}

    values = compute_candidate_static_values(
        scenario,
        snapshot_seconds=snapshot_seconds,
    )
    scenario.candidate_windows = [
        CandidateWindow(
            window_id=window.window_id,
            a=window.a,
            b=window.b,
            start=window.start,
            end=window.end,
            value=values.get(window.window_id, 0.0),
            delay=window.delay,
            distance_km=window.distance_km,
        )
        for window in scenario.candidate_windows
    ]
    scenario.metadata.setdefault("stage1_static_value", {})
    scenario.metadata["stage1_static_value"]["snapshot_seconds"] = (
        scenario.stage1.static_value_snapshot_seconds if snapshot_seconds is None else snapshot_seconds
    )
    return values
