from __future__ import annotations

import math
import random
import time
from bisect import insort
from dataclasses import dataclass
from typing import Iterable

import networkx as nx

from .models import CandidateWindow, HotspotRegion, ScheduledWindow, Scenario, Stage1Candidate, Stage1Result, Task
from .scenario import active_cross_links, active_intra_links, build_domain_graph, build_segments
from .stage1_static_value import annotate_scenario_candidate_values

EPS = 1e-9
PRUNE_EXACT_LIMIT = 8
TOURNAMENT_SIZE = 3


class ResourceCalendar:
    def __init__(self, nodes: Iterable[str]) -> None:
        self._calendar: dict[str, list[tuple[float, float]]] = {node: [] for node in nodes}

    def latest_end_before(self, node: str, time_end: float, t_pre: float) -> float:
        latest = -t_pre
        for start, end in self._calendar[node]:
            if start < time_end and end > latest:
                latest = end
        return latest

    def add_interval(self, node: str, interval: tuple[float, float]) -> None:
        insort(self._calendar[node], interval)


def try_insert_window(
    window: CandidateWindow,
    resource_calendar: ResourceCalendar,
    t_pre: float,
    d_min: float,
) -> ScheduledWindow | None:
    e_a = resource_calendar.latest_end_before(window.a, window.end, t_pre)
    e_b = resource_calendar.latest_end_before(window.b, window.end, t_pre)
    t_on = max(window.start, e_a + t_pre, e_b + t_pre)
    if window.end - t_on < d_min:
        return None

    occupied = (t_on - t_pre, window.end)
    resource_calendar.add_interval(window.a, occupied)
    resource_calendar.add_interval(window.b, occupied)
    return ScheduledWindow(
        window_id=window.window_id,
        a=window.a,
        b=window.b,
        start=window.start,
        end=window.end,
        on=t_on,
        off=window.end,
        value=window.value,
        delay=window.delay,
        distance_km=window.distance_km,
    )


def plan_signature(plan: list[ScheduledWindow]) -> tuple[tuple[str, float, float], ...]:
    signature = [(window.window_id, round(window.on, 9), round(window.off, 9)) for window in plan]
    signature.sort()
    return tuple(signature)


def gateway_count(plan: list[ScheduledWindow]) -> int:
    return len({node for window in plan for node in (window.a, window.b)})


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged: list[tuple[float, float]] = []
    cur_start, cur_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= cur_end + EPS:
            cur_end = max(cur_end, end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))
    return merged


def gateway_activation_intervals(plan: list[ScheduledWindow], t_pre: float) -> dict[str, list[tuple[float, float]]]:
    intervals_by_node: dict[str, list[tuple[float, float]]] = {}
    for window in plan:
        interval = (window.on - t_pre, window.off)
        intervals_by_node.setdefault(window.a, []).append(interval)
        intervals_by_node.setdefault(window.b, []).append(interval)
    return {node: _merge_intervals(intervals) for node, intervals in intervals_by_node.items()}


def activation_count(plan: list[ScheduledWindow], t_pre: float) -> int:
    del t_pre
    return 2 * len(plan)


def activation_time(plan: list[ScheduledWindow], t_pre: float) -> float:
    return sum(
        end - start
        for intervals in gateway_activation_intervals(plan, t_pre).values()
        for start, end in intervals
    )


def occupation_time(plan: list[ScheduledWindow], t_pre: float) -> float:
    return activation_time(plan, t_pre)


def merged_cross_intervals(plan: list[ScheduledWindow]) -> list[tuple[float, float]]:
    return _merge_intervals(sorted((window.on, window.off) for window in plan))


def cross_active_fraction(plan: list[ScheduledWindow], planning_end: float) -> float:
    if planning_end <= EPS:
        return 0.0
    active = sum(end - start for start, end in merged_cross_intervals(plan))
    return active / planning_end


def max_cross_gap(plan: list[ScheduledWindow], planning_end: float) -> float:
    if planning_end <= EPS:
        return 0.0
    merged = merged_cross_intervals(plan)
    if not merged:
        return planning_end
    longest = max(0.0, merged[0][0])
    prev_end = merged[0][1]
    for start, end in merged[1:]:
        longest = max(longest, max(0.0, start - prev_end))
        prev_end = max(prev_end, end)
    return max(longest, max(0.0, planning_end - prev_end))


@dataclass(frozen=True)
class EvaluationMetrics:
    sr_theta_c: float
    eta_cap: float
    eta_0: float


@dataclass(frozen=True)
class StructuralMetrics:
    activation_count: int
    activation_time: float
    unique_gateway_count: int
    avg_hot_coverage: float
    max_hot_gap: float
    cross_active_fraction: float
    max_cross_gap: float
    proxy_eta_cap: float


@dataclass
class SimulationTrace:
    metrics: EvaluationMetrics
    segment_rows: list[dict]
    task_rows: list[dict]
    window_rows: list[dict]
    window_flow: dict[str, float]


@dataclass
class OrderState:
    order: tuple[str, ...]
    plan: list[ScheduledWindow]
    metrics: EvaluationMetrics
    structural: StructuralMetrics
    feasible: bool
    violation: float
    fitness: tuple[float, ...]


@dataclass(frozen=True)
class DomainPath:
    nodes: tuple[str, ...]
    edge_ids: tuple[str, ...]
    delay: float


@dataclass(frozen=True)
class PathOption:
    path_key: tuple[str, ...]
    edge_ids: tuple[str, ...]
    cross_window_id: str
    delay: float
    candidate_rate: float
    candidate_delivered: float
    effective_duration: float
    predicted_cross_load: float
    hop_count: int


class RegularEvaluator:
    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.regular_tasks = [
            task
            for task in scenario.tasks
            if task.task_type == "reg" and scenario.node_domain[task.src] != scenario.node_domain[task.dst]
        ]
        self.total_weight = sum(task.weight for task in self.regular_tasks)
        self._trace_cache: dict[tuple[tuple[tuple[str, float, float], ...], float], SimulationTrace] = {}
        self._domain_path_cache: dict[tuple[str, float, str, str, str | None], DomainPath | None] = {}

    def _trace_key(self, plan: list[ScheduledWindow], rho: float) -> tuple[tuple[tuple[str, float, float], ...], float]:
        return (plan_signature(plan), round(rho, 9))

    @staticmethod
    def _distance_weight(data: dict) -> float:
        distance = data.get("distance_km")
        if distance is not None:
            return float(distance)
        return float(data.get("weight", 1.0))

    def _domain_shortest_path(
        self,
        domain: str,
        time_point: float,
        src: str,
        dst: str,
        blocked_edge_id: str | None = None,
    ) -> DomainPath | None:
        cache_key = (domain, float(time_point), src, dst, blocked_edge_id)
        if cache_key in self._domain_path_cache:
            return self._domain_path_cache[cache_key]

        if src == dst:
            path = DomainPath(nodes=(src,), edge_ids=tuple(), delay=0.0)
            self._domain_path_cache[cache_key] = path
            return path

        graph = build_domain_graph(self.scenario, domain, time_point)
        if src not in graph or dst not in graph:
            self._domain_path_cache[cache_key] = None
            return None

        work_graph = graph
        if blocked_edge_id is not None:
            removable = [
                (u, v)
                for u, v, data in graph.edges(data=True)
                if str(data.get("edge_id")) == blocked_edge_id
            ]
            if removable:
                work_graph = graph.copy()
                work_graph.remove_edges_from(removable)

        try:
            nodes = tuple(
                nx.shortest_path(
                    work_graph,
                    src,
                    dst,
                    weight=lambda u, v, data: self._distance_weight(data),
                )
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self._domain_path_cache[cache_key] = None
            return None

        edge_ids: list[str] = []
        delay = 0.0
        for u, v in zip(nodes, nodes[1:]):
            data = work_graph[u][v]
            edge_ids.append(str(data["edge_id"]))
            delay += float(data.get("delay", 0.0))
        path = DomainPath(nodes=nodes, edge_ids=tuple(edge_ids), delay=delay)
        self._domain_path_cache[cache_key] = path
        return path

    @staticmethod
    def _domain_bottleneck(
        edge_ids: tuple[str, ...],
        cap_res: dict[str, float],
    ) -> tuple[float, str | None]:
        if not edge_ids:
            return float("inf"), None
        bottleneck_value = float("inf")
        bottleneck_edge: str | None = None
        for edge_id in edge_ids:
            value = cap_res.get(edge_id, -float("inf"))
            if value < bottleneck_value:
                bottleneck_value = value
                bottleneck_edge = edge_id
        return bottleneck_value, bottleneck_edge

    @staticmethod
    def _build_edge_sequence(
        window: ScheduledWindow,
        left_path: DomainPath,
        right_path: DomainPath,
    ) -> tuple[tuple[str, ...], tuple[str, ...], int]:
        nodes = left_path.nodes + right_path.nodes
        edge_ids = left_path.edge_ids + (window.window_id,) + right_path.edge_ids
        return nodes, edge_ids, len(edge_ids)

    def _cross_path_candidates(
        self,
        task: Task,
        window: ScheduledWindow,
        segment_start: float,
        cap_res: dict[str, float],
    ) -> list[tuple[tuple[str, ...], tuple[str, ...], float, int]]:
        src_domain = self.scenario.node_domain[task.src]
        dst_domain = self.scenario.node_domain[task.dst]
        if src_domain == dst_domain:
            return []

        if src_domain == "A" and dst_domain == "B":
            left_primary = self._domain_shortest_path("A", segment_start, task.src, window.a)
            right_primary = self._domain_shortest_path("B", segment_start, window.b, task.dst)
        elif src_domain == "B" and dst_domain == "A":
            left_primary = self._domain_shortest_path("B", segment_start, task.src, window.b)
            right_primary = self._domain_shortest_path("A", segment_start, window.a, task.dst)
        else:
            return []

        if left_primary is None or right_primary is None:
            return []

        primary_nodes, primary_edges, primary_hops = self._build_edge_sequence(window, left_primary, right_primary)
        primary_delay = left_primary.delay + float(window.delay) + right_primary.delay
        candidates = [(primary_nodes, primary_edges, primary_delay, primary_hops)]

        bottleneck_a, edge_a = self._domain_bottleneck(left_primary.edge_ids, cap_res)
        bottleneck_b, edge_b = self._domain_bottleneck(right_primary.edge_ids, cap_res)
        bottleneck_x = cap_res.get(window.window_id, 0.0)
        side_scores = []
        if edge_a is not None:
            side_scores.append(
                (
                    bottleneck_a / max(min(bottleneck_x, bottleneck_b), EPS),
                    "left",
                    edge_a,
                )
            )
        if edge_b is not None:
            side_scores.append(
                (
                    bottleneck_b / max(min(bottleneck_x, bottleneck_a), EPS),
                    "right",
                    edge_b,
                )
            )
        side_scores = [item for item in side_scores if item[0] <= self.scenario.stage1.bottleneck_factor_alpha + EPS]
        if not side_scores:
            return candidates

        side_scores.sort(key=lambda item: item[0])
        _, side, blocked_edge = side_scores[0]
        if side == "left":
            if src_domain == "A" and dst_domain == "B":
                left_backup = self._domain_shortest_path("A", segment_start, task.src, window.a, blocked_edge)
            else:
                left_backup = self._domain_shortest_path("B", segment_start, task.src, window.b, blocked_edge)
            if left_backup is None or left_backup.edge_ids == left_primary.edge_ids:
                return candidates
            backup_nodes, backup_edges, backup_hops = self._build_edge_sequence(window, left_backup, right_primary)
            backup_delay = left_backup.delay + float(window.delay) + right_primary.delay
        else:
            if src_domain == "A" and dst_domain == "B":
                right_backup = self._domain_shortest_path("B", segment_start, window.b, task.dst, blocked_edge)
            else:
                right_backup = self._domain_shortest_path("A", segment_start, window.a, task.dst, blocked_edge)
            if right_backup is None or right_backup.edge_ids == right_primary.edge_ids:
                return candidates
            backup_nodes, backup_edges, backup_hops = self._build_edge_sequence(window, left_primary, right_backup)
            backup_delay = left_primary.delay + float(window.delay) + right_backup.delay

        if backup_edges != primary_edges:
            candidates.append((backup_nodes, backup_edges, backup_delay, backup_hops))
        return candidates

    def _task_path_options(
        self,
        task: Task,
        segment,
        active_windows: list[ScheduledWindow],
        cap_res: dict[str, float],
        cross_used: dict[str, float],
        remaining_task: float,
        prev_path_key: tuple[str, ...] | None,
        cross_reg_capacity: float,
    ) -> list[PathOption]:
        remaining_slack = max(task.deadline - segment.start, EPS)
        options: list[PathOption] = []
        for window in active_windows:
            for _, edge_ids, delay, hop_count in self._cross_path_candidates(task, window, segment.start, cap_res):
                if delay >= remaining_slack:
                    continue
                effective_duration = max(
                    0.0,
                    min(segment.end, task.deadline - delay) - segment.start,
                )
                if effective_duration <= EPS:
                    continue
                bottleneck = min(cap_res.get(edge_id, 0.0) for edge_id in edge_ids)
                if bottleneck <= EPS:
                    continue
                candidate_rate = min(task.max_rate, bottleneck, remaining_task / effective_duration)
                if candidate_rate <= EPS:
                    continue
                candidate_delivered = candidate_rate * effective_duration
                if candidate_delivered <= EPS:
                    continue
                predicted_cross_load = (cross_used[window.window_id] + candidate_rate) / max(cross_reg_capacity, EPS)
                path_key = tuple(edge_ids)
                options.append(
                    PathOption(
                        path_key=path_key,
                        edge_ids=edge_ids,
                        cross_window_id=window.window_id,
                        delay=delay,
                        candidate_rate=candidate_rate,
                        candidate_delivered=candidate_delivered,
                        effective_duration=effective_duration,
                        predicted_cross_load=predicted_cross_load,
                        hop_count=hop_count,
                    )
                )
        if not options:
            return []

        max_delivered = max(option.candidate_delivered for option in options)
        near_threshold = self.scenario.stage1.eta_x * max_delivered
        near_options = [
            option
            for option in options
            if option.candidate_delivered + EPS >= near_threshold
        ]
        near_options.sort(
            key=lambda option: (
                option.predicted_cross_load,
                option.delay,
                0 if prev_path_key is not None and option.path_key == prev_path_key else 1,
                option.hop_count,
                option.edge_ids,
            )
        )
        return near_options

    def _simulate(self, plan: list[ScheduledWindow], rho: float) -> SimulationTrace:
        if not self.regular_tasks:
            return SimulationTrace(
                metrics=EvaluationMetrics(sr_theta_c=1.0, eta_cap=0.0, eta_0=0.0),
                segment_rows=[],
                task_rows=[],
                window_rows=[],
                window_flow={},
            )

        segments = build_segments(self.scenario, plan, self.regular_tasks)
        remaining = {task.task_id: task.data for task in self.regular_tasks}
        prev_path_keys: dict[str, tuple[str, ...] | None] = {task.task_id: None for task in self.regular_tasks}
        cross_reg_capacity = max((1.0 - rho) * self.scenario.capacities.cross, EPS)
        theta_c = self.scenario.stage1.theta_c

        demand_weighted_total = 0.0
        eta_cap_numerator = 0.0
        eta0_numerator = 0.0
        window_flow: dict[str, float] = {window.window_id: 0.0 for window in plan}
        segment_rows: list[dict] = []

        for segment in segments:
            if segment.duration <= EPS:
                continue

            active_tasks = [
                task
                for task in self.regular_tasks
                if task.arrival <= segment.start < task.deadline and remaining[task.task_id] > EPS
            ]
            cross_now = active_cross_links(plan, segment.start)
            cross_supply = len(cross_now) * max((1.0 - rho) * self.scenario.capacities.cross, 0.0)
            cross_demand_req = sum(
                min(task.max_rate, remaining[task.task_id] / max(task.deadline - segment.start, EPS))
                for task in active_tasks
            )
            demand_weighted_total += cross_demand_req * segment.duration
            eta_cap_numerator += max(cross_demand_req - cross_supply, 0.0) * segment.duration
            if cross_demand_req > EPS and not cross_now:
                eta0_numerator += cross_demand_req * segment.duration

            cap_res: dict[str, float] = {}
            for link in active_intra_links(self.scenario, "A", segment.start):
                cap_res[link.link_id] = self.scenario.capacities.domain_a
            for link in active_intra_links(self.scenario, "B", segment.start):
                cap_res[link.link_id] = self.scenario.capacities.domain_b
            for window in cross_now:
                cap_res[window.window_id] = cross_reg_capacity
            cross_used = {window.window_id: 0.0 for window in cross_now}
            served_this_segment: set[str] = set()
            segment_cross_data_used = 0.0

            active_tasks.sort(
                key=lambda task: (
                    -task.weight,
                    -(remaining[task.task_id] / max(task.deadline - segment.start, EPS)),
                    -remaining[task.task_id],
                    task.task_id,
                )
            )

            for task in active_tasks:
                remaining_task = remaining[task.task_id]
                if remaining_task <= EPS:
                    continue
                options = self._task_path_options(
                    task=task,
                    segment=segment,
                    active_windows=cross_now,
                    cap_res=cap_res,
                    cross_used=cross_used,
                    remaining_task=remaining_task,
                    prev_path_key=prev_path_keys[task.task_id],
                    cross_reg_capacity=cross_reg_capacity,
                )
                if not options:
                    continue

                selected = options[0]
                delivered = selected.candidate_delivered
                for edge_id in selected.edge_ids:
                    cap_res[edge_id] -= selected.candidate_rate
                cross_used[selected.cross_window_id] += selected.candidate_rate
                window_flow[selected.cross_window_id] += delivered
                segment_cross_data_used += delivered
                remaining[task.task_id] = max(0.0, remaining_task - delivered)
                prev_path_keys[task.task_id] = selected.path_key
                served_this_segment.add(task.task_id)

            for task in active_tasks:
                if task.task_id not in served_this_segment:
                    prev_path_keys[task.task_id] = None

            segment_rows.append(
                {
                    "segment_index": segment.index,
                    "start": segment.start,
                    "end": segment.end,
                    "duration": segment.duration,
                    "active_task_count": len(active_tasks),
                    "demand_req": cross_demand_req,
                    "cross_demand_req": cross_demand_req,
                    "required_cross_link_count": (
                        int(math.ceil(cross_demand_req / cross_reg_capacity))
                        if cross_demand_req > EPS
                        else 0
                    ),
                    "cross_link_count": len(cross_now),
                    "cross_capacity": cross_supply,
                    "cross_supply": cross_supply,
                    "cross_rate_used": sum(cross_used.values()),
                    "cross_data_used": segment_cross_data_used,
                    "eta_cap_shortfall": max(cross_demand_req - cross_supply, 0.0),
                    "zero_cross_req": 1 if cross_demand_req > EPS and not cross_now else 0,
                    "zero_cross_demand": 1 if cross_demand_req > EPS and not cross_now else 0,
                    "eta0_indicator": 1 if cross_demand_req > EPS and not cross_now else 0,
                }
            )

        weighted_near = 0.0
        task_rows: list[dict] = []
        for task in self.regular_tasks:
            phi = 1.0 - remaining[task.task_id] / task.data
            near_complete = 1 if phi + EPS >= theta_c else 0
            if near_complete:
                weighted_near += task.weight
            task_rows.append(
                {
                    "task_id": task.task_id,
                    "src": task.src,
                    "dst": task.dst,
                    "arrival": task.arrival,
                    "deadline": task.deadline,
                    "data": task.data,
                    "weight": task.weight,
                    "max_rate": task.max_rate,
                    "remaining_end": remaining[task.task_id],
                    "completion_ratio": phi,
                    "near_complete": near_complete,
                    "completed": 1 if remaining[task.task_id] <= EPS else 0,
                }
            )

        window_rows = [
            {
                "window_id": window.window_id,
                "a": window.a,
                "b": window.b,
                "on": window.on,
                "off": window.off,
                "delivered": window_flow.get(window.window_id, 0.0),
            }
            for window in sorted(plan, key=lambda item: (item.on, item.off, item.window_id))
        ]
        metrics = EvaluationMetrics(
            sr_theta_c=(weighted_near / self.total_weight) if self.total_weight > EPS else 1.0,
            eta_cap=(eta_cap_numerator / (demand_weighted_total + EPS)) if demand_weighted_total > EPS else 0.0,
            eta_0=(eta0_numerator / (demand_weighted_total + EPS)) if demand_weighted_total > EPS else 0.0,
        )
        return SimulationTrace(
            metrics=metrics,
            segment_rows=segment_rows,
            task_rows=task_rows,
            window_rows=window_rows,
            window_flow=window_flow,
        )

    def trace(self, plan: list[ScheduledWindow], rho: float | None = None, k_paths: int | None = None) -> dict:
        del k_paths
        rho = self.scenario.stage1.rho if rho is None else rho
        cache_key = self._trace_key(plan, rho)
        if cache_key not in self._trace_cache:
            self._trace_cache[cache_key] = self._simulate(plan, rho=rho)
        trace = self._trace_cache[cache_key]
        return {
            "metrics": {
                "sr_theta_c": trace.metrics.sr_theta_c,
                "sr_near": trace.metrics.sr_theta_c,
                "eta_cap": trace.metrics.eta_cap,
                "eta_0": trace.metrics.eta_0,
                "cross_capacity_gap": trace.metrics.eta_cap,
                "zero_cross_demand_ratio": trace.metrics.eta_0,
            },
            "segments": trace.segment_rows,
            "tasks": trace.task_rows,
            "windows": trace.window_rows,
        }

    def evaluate(self, plan: list[ScheduledWindow], rho: float | None = None, k_paths: int | None = None) -> EvaluationMetrics:
        del k_paths
        rho = self.scenario.stage1.rho if rho is None else rho
        cache_key = self._trace_key(plan, rho)
        if cache_key not in self._trace_cache:
            self._trace_cache[cache_key] = self._simulate(plan, rho=rho)
        return self._trace_cache[cache_key].metrics

    def window_flow(self, plan: list[ScheduledWindow], rho: float | None = None, k_paths: int | None = None) -> dict[str, float]:
        del k_paths
        rho = self.scenario.stage1.rho if rho is None else rho
        cache_key = self._trace_key(plan, rho)
        if cache_key not in self._trace_cache:
            self._trace_cache[cache_key] = self._simulate(plan, rho=rho)
        return dict(self._trace_cache[cache_key].window_flow)


class PlanAnalyzer:
    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.cross_regular_tasks = [
            task
            for task in scenario.tasks
            if task.task_type == "reg" and scenario.node_domain[task.src] != scenario.node_domain[task.dst]
        ]
        self._base_segments = build_segments(scenario, [], self.cross_regular_tasks)
        self._hot_cache: dict[tuple[tuple[str, float, float], ...], tuple[float, float]] = {}
        self._structural_cache: dict[tuple[tuple[str, float, float], ...], StructuralMetrics] = {}

    def proxy_eta_cap(self, plan: list[ScheduledWindow]) -> float:
        cross_reg_capacity = max((1.0 - self.scenario.stage1.rho) * self.scenario.capacities.cross, 0.0)
        numerator = 0.0
        denominator = 0.0
        for segment in self._base_segments:
            if segment.duration <= EPS:
                continue
            demand_hat = sum(
                min(task.max_rate, task.data / max(task.deadline - task.arrival, EPS))
                for task in self.cross_regular_tasks
                if task.arrival <= segment.start < task.deadline
            )
            if demand_hat <= EPS:
                continue
            cross_count = len(active_cross_links(plan, segment.start))
            supply = cross_count * cross_reg_capacity
            numerator += max(demand_hat - supply, 0.0) * segment.duration
            denominator += demand_hat * segment.duration
        return numerator / (denominator + EPS) if denominator > EPS else 0.0

    def _hot_metrics(self, plan: list[ScheduledWindow]) -> tuple[float, float]:
        hotspots: list[HotspotRegion] = self.scenario.hotspots_a
        if not hotspots:
            return 1.0, 0.0

        segments = build_segments(self.scenario, plan, [])
        if not segments:
            return 1.0, 0.0

        covered_numerator = 0.0
        active_denominator = 0.0
        uncovered_run = 0.0
        uncovered_max = 0.0
        hop_limit = self.scenario.stage1.hot_hop_limit
        hotspot_reach_cache = self.scenario.metadata.setdefault("_runtime_cache", {}).setdefault("hotspot_reachability", {})

        for segment in segments:
            if segment.duration <= EPS:
                continue
            active_windows = active_cross_links(plan, segment.start)
            active_weight = 0.0
            covered_weight = 0.0
            if active_windows:
                gateways = {window.a for window in active_windows}
                graph_a = build_domain_graph(self.scenario, "A", segment.start)
                for region in hotspots:
                    nodes = region.active_nodes(segment.start)
                    if not nodes:
                        continue
                    active_weight += region.weight
                    cache_key = (float(segment.start), tuple(nodes), int(hop_limit))
                    reachable_gateways = hotspot_reach_cache.get(cache_key)
                    if reachable_gateways is None:
                        reachable: set[str] = set()
                        for node in nodes:
                            if node not in graph_a:
                                continue
                            hop_map = nx.single_source_shortest_path_length(graph_a, node, cutoff=hop_limit)
                            reachable.update(hop_map)
                        reachable_gateways = frozenset(reachable)
                        hotspot_reach_cache[cache_key] = reachable_gateways
                    if gateways.intersection(reachable_gateways):
                        covered_weight += region.weight
            else:
                for region in hotspots:
                    if region.active_nodes(segment.start):
                        active_weight += region.weight

            if active_weight <= EPS:
                uncovered_run = 0.0
                continue

            normalized_coverage = covered_weight / active_weight
            covered_numerator += covered_weight * segment.duration
            active_denominator += active_weight * segment.duration

            if normalized_coverage <= EPS:
                uncovered_run += segment.duration
                uncovered_max = max(uncovered_max, uncovered_run)
            else:
                uncovered_run = 0.0

        avg_coverage = covered_numerator / max(active_denominator, EPS) if active_denominator > EPS else 1.0
        return avg_coverage, uncovered_max

    def hot_metrics(self, plan: list[ScheduledWindow]) -> tuple[float, float]:
        signature = plan_signature(plan)
        cached = self._hot_cache.get(signature)
        if cached is not None:
            return cached
        metrics = self._hot_metrics(plan)
        self._hot_cache[signature] = metrics
        return metrics

    def evaluate(self, plan: list[ScheduledWindow]) -> StructuralMetrics:
        signature = plan_signature(plan)
        cached = self._structural_cache.get(signature)
        if cached is not None:
            return cached

        avg_hot_coverage, max_hot_gap = self.hot_metrics(plan)
        metrics = StructuralMetrics(
            activation_count=activation_count(plan, self.scenario.stage1.t_pre),
            activation_time=activation_time(plan, self.scenario.stage1.t_pre),
            unique_gateway_count=gateway_count(plan),
            avg_hot_coverage=avg_hot_coverage,
            max_hot_gap=max_hot_gap,
            cross_active_fraction=cross_active_fraction(plan, self.scenario.planning_end),
            max_cross_gap=max_cross_gap(plan, self.scenario.planning_end),
            proxy_eta_cap=self.proxy_eta_cap(plan),
        )
        self._structural_cache[signature] = metrics
        return metrics


class Stage1GA:
    def __init__(self, scenario: Scenario, seed: int | None = None) -> None:
        self.scenario = scenario
        annotate_scenario_candidate_values(self.scenario)
        self.random = random.Random(seed)
        self._started_at: float | None = None
        self.windows_by_id = {window.window_id: window for window in scenario.candidate_windows}
        self.window_ids = [window.window_id for window in scenario.candidate_windows]
        self.evaluator = RegularEvaluator(scenario)
        self.plan_analyzer = PlanAnalyzer(scenario)
        self._decode_order_cache: dict[tuple[str, ...], list[ScheduledWindow]] = {}
        self._decoded_acceptance_cache: dict[tuple[str, ...], tuple[str, ...]] = {}
        self._order_state_cache: dict[tuple[str, ...], OrderState] = {}
        self._candidate_cache: dict[tuple[str, ...], Stage1Candidate] = {}

    def _time_exceeded(self, started_at: float) -> bool:
        limit = self.scenario.stage1.ga.max_runtime_seconds
        return limit is not None and limit > 0 and (time.perf_counter() - started_at) >= limit - EPS

    def _violation(self, metrics: EvaluationMetrics, structural: StructuralMetrics) -> float:
        theta_sr = max(self.scenario.stage1.theta_sr, EPS)
        theta_cap = max(self.scenario.stage1.theta_cap, EPS)
        theta_hot = max(self.scenario.stage1.theta_hot, EPS)
        v_sr = max(0.0, self.scenario.stage1.theta_sr - metrics.sr_theta_c)
        v_cap = max(0.0, metrics.eta_cap - self.scenario.stage1.theta_cap)
        v_hot = max(0.0, self.scenario.stage1.theta_hot - structural.avg_hot_coverage)
        return (
            self.scenario.stage1.omega_sr * v_sr / theta_sr
            + self.scenario.stage1.omega_cap * v_cap / theta_cap
            + self.scenario.stage1.omega_hot * v_hot / theta_hot
        )

    def _feasible(self, metrics: EvaluationMetrics, structural: StructuralMetrics) -> bool:
        return (
            metrics.sr_theta_c + EPS >= self.scenario.stage1.theta_sr
            and metrics.eta_cap <= self.scenario.stage1.theta_cap + EPS
            and structural.avg_hot_coverage + EPS >= self.scenario.stage1.theta_hot
        )

    def _fitness(self, metrics: EvaluationMetrics, structural: StructuralMetrics, feasible: bool, violation: float) -> tuple[float, ...]:
        if feasible:
            return (
                0.0,
                float(structural.activation_count),
                -float(metrics.sr_theta_c),
                float(metrics.eta_cap),
                -float(structural.avg_hot_coverage),
            )
        return (
            1.0,
            float(violation),
            -float(metrics.sr_theta_c),
            float(metrics.eta_cap),
            -float(structural.avg_hot_coverage),
            float(structural.activation_count),
        )

    def _build_plan(self, order: Iterable[str]) -> list[ScheduledWindow]:
        calendar = ResourceCalendar(self.scenario.node_domain.keys())
        plan: list[ScheduledWindow] = []
        for window_id in order:
            window = self.windows_by_id[window_id]
            scheduled = try_insert_window(window, calendar, self.scenario.stage1.t_pre, self.scenario.stage1.d_min)
            if scheduled is not None:
                plan.append(scheduled)
        return plan

    def _decode_order(self, order: Iterable[str]) -> list[ScheduledWindow]:
        order_key = tuple(order)
        if order_key not in self._decode_order_cache:
            self._decode_order_cache[order_key] = self._build_plan(order_key)
        return self._decode_order_cache[order_key]

    def _analyze_order(self, order: Iterable[str]) -> OrderState:
        order_key = tuple(order)
        cached = self._order_state_cache.get(order_key)
        if cached is not None:
            return cached

        plan = self._decode_order(order_key)
        metrics = self.evaluator.evaluate(plan)
        structural = self.plan_analyzer.evaluate(plan)
        feasible = self._feasible(metrics, structural)
        violation = 0.0 if feasible else self._violation(metrics, structural)
        fitness = self._fitness(metrics, structural, feasible, violation)
        state = OrderState(
            order=order_key,
            plan=plan,
            metrics=metrics,
            structural=structural,
            feasible=feasible,
            violation=violation,
            fitness=fitness,
        )
        self._order_state_cache[order_key] = state
        return state

    def _decode_accepted_order(self, chromosome: tuple[str, ...]) -> tuple[str, ...]:
        cached = self._decoded_acceptance_cache.get(chromosome)
        if cached is not None:
            return cached

        calendar = ResourceCalendar(self.scenario.node_domain.keys())
        accepted_order: list[str] = []
        q_eval = max(1, self.scenario.stage1.q_eval)

        for window_id in chromosome:
            if self._started_at is not None and self._time_exceeded(self._started_at):
                decoded = tuple(accepted_order)
                self._decoded_acceptance_cache[chromosome] = decoded
                return decoded
            window = self.windows_by_id[window_id]
            scheduled = try_insert_window(window, calendar, self.scenario.stage1.t_pre, self.scenario.stage1.d_min)
            if scheduled is None:
                continue
            accepted_order.append(window_id)
            if len(accepted_order) % q_eval != 0:
                continue
            state = self._analyze_order(accepted_order)
            if state.feasible:
                decoded = tuple(state.order)
                self._decoded_acceptance_cache[chromosome] = decoded
                return decoded

        decoded = tuple(accepted_order)
        self._decoded_acceptance_cache[chromosome] = decoded
        return decoded

    def _candidate_from_state(self, original_chromosome: tuple[str, ...], state: OrderState) -> Stage1Candidate:
        accepted = tuple(state.order)
        accepted_set = set(accepted)
        feedback = accepted + tuple(gene for gene in original_chromosome if gene not in accepted_set)
        return Stage1Candidate(
            chromosome=feedback,
            accepted_order=accepted,
            plan=state.plan,
            feasible=state.feasible,
            violation=state.violation,
            sr_theta_c=state.metrics.sr_theta_c,
            eta_cap=state.metrics.eta_cap,
            eta_0=state.metrics.eta_0,
            avg_hot_coverage=state.structural.avg_hot_coverage,
            max_hot_gap=state.structural.max_hot_gap,
            activation_count=state.structural.activation_count,
            activation_time=state.structural.activation_time,
            unique_gateway_count=state.structural.unique_gateway_count,
            window_count=len(state.plan),
            cross_active_fraction=state.structural.cross_active_fraction,
            max_cross_gap=state.structural.max_cross_gap,
            fitness=state.fitness,
        )

    def _evaluate_chromosome(self, chromosome: Iterable[str]) -> Stage1Candidate:
        chromosome_tuple = tuple(chromosome)
        cached = self._candidate_cache.get(chromosome_tuple)
        if cached is not None:
            return cached

        accepted_order = self._decode_accepted_order(chromosome_tuple)
        state = self._analyze_order(accepted_order)
        candidate = self._candidate_from_state(chromosome_tuple, state)
        self._candidate_cache[chromosome_tuple] = candidate
        self._candidate_cache[candidate.chromosome] = candidate
        return candidate

    def _sorted_windows_by_value(self) -> list[str]:
        windows = sorted(
            self.scenario.candidate_windows,
            key=lambda item: (item.value if item.value is not None else item.duration),
            reverse=True,
        )
        return [window.window_id for window in windows]

    def _sorted_windows_by_density(self) -> list[str]:
        windows = sorted(
            self.scenario.candidate_windows,
            key=lambda item: (item.value if item.value is not None else item.duration) / max(self.scenario.stage1.t_pre + item.duration, EPS),
            reverse=True,
        )
        return [window.window_id for window in windows]

    def _rcl_chromosome(self) -> list[str]:
        remaining = self._sorted_windows_by_density()
        chromosome: list[str] = []
        while remaining:
            rcl_size = min(len(remaining), max(5, math.ceil(0.1 * len(remaining))))
            idx = self.random.randrange(rcl_size)
            chromosome.append(remaining.pop(idx))
        return chromosome

    def _random_chromosome(self) -> list[str]:
        genes = self.window_ids[:]
        self.random.shuffle(genes)
        return genes

    def _initial_population(self) -> list[list[str]]:
        total = self.scenario.stage1.ga.population_size
        if not self.window_ids:
            return [[] for _ in range(total)]

        by_value = self._sorted_windows_by_value()
        by_density = self._sorted_windows_by_density()
        count_value = max(1, round(total * 0.1))
        count_density = max(1, round(total * 0.1))
        count_rcl = max(1, round(total * 0.6))
        count_random = max(0, total - count_value - count_density - count_rcl)

        population: list[list[str]] = []
        population.extend([by_value[:] for _ in range(count_value)])
        population.extend([by_density[:] for _ in range(count_density)])
        population.extend([self._rcl_chromosome() for _ in range(count_rcl)])
        population.extend([self._random_chromosome() for _ in range(count_random)])
        return population[:total]

    def _tournament_select(self, population: list[Stage1Candidate]) -> Stage1Candidate:
        sample = self.random.sample(population, min(TOURNAMENT_SIZE, len(population)))
        return min(sample, key=lambda item: item.fitness)

    def _prefix_crossover(self, parent_a: tuple[str, ...], parent_b: tuple[str, ...]) -> list[str]:
        if len(parent_a) <= 1:
            return list(parent_a)
        cut = self.random.randint(1, len(parent_a) - 1)
        child = list(parent_a[:cut])
        seen = set(child)
        child.extend(gene for gene in parent_b if gene not in seen)
        return child

    def _mutate(self, chromosome: list[str]) -> list[str]:
        if len(chromosome) <= 1:
            return chromosome
        mutated = chromosome[:]
        if self.random.random() < 0.7:
            src = self.random.randrange(len(mutated))
            gene = mutated.pop(src)
            dst = self.random.randrange(len(mutated) + 1)
            mutated.insert(dst, gene)
        else:
            i, j = self.random.sample(range(len(mutated)), 2)
            mutated[i], mutated[j] = mutated[j], mutated[i]
        return mutated

    def _update_archive(self, archive: list[Stage1Candidate], population: list[Stage1Candidate]) -> list[Stage1Candidate]:
        all_candidates = archive[:]
        signatures = {plan_signature(candidate.plan) for candidate in archive}
        for candidate in population:
            if not candidate.feasible:
                continue
            signature = plan_signature(candidate.plan)
            if signature in signatures:
                continue
            all_candidates.append(candidate)
            signatures.add(signature)
        all_candidates.sort(key=lambda item: item.fitness)
        return all_candidates[: self.scenario.stage1.ga.top_m]

    def _prune_candidate(self, candidate: Stage1Candidate) -> Stage1Candidate:
        if not candidate.feasible or not candidate.accepted_order:
            return candidate

        current_state = self._analyze_order(candidate.accepted_order)
        current_order = list(current_state.order)

        while True:
            current_proxy = current_state.structural.proxy_eta_cap
            window_flow = self.evaluator.window_flow(current_state.plan)
            ranked_trials: list[tuple[float, float, float, OrderState]] = []

            for idx, window_id in enumerate(current_order):
                trial_order = current_order[:idx] + current_order[idx + 1 :]
                trial_plan = self._decode_order(trial_order)
                trial_structural = self.plan_analyzer.evaluate(trial_plan)
                if trial_structural.proxy_eta_cap > self.scenario.stage1.theta_cap + EPS:
                    continue
                if trial_structural.avg_hot_coverage + EPS < self.scenario.stage1.theta_hot:
                    continue

                trial_state = self._analyze_order(trial_order)
                ranked_trials.append(
                    (
                        window_flow.get(window_id, 0.0),
                        trial_structural.proxy_eta_cap - current_proxy,
                        current_state.structural.avg_hot_coverage - trial_structural.avg_hot_coverage,
                        trial_state,
                    )
                )

            if not ranked_trials:
                break

            ranked_trials.sort(key=lambda item: (item[0], item[1], item[2], item[3].fitness))
            accepted = False
            for _, _, _, trial_state in ranked_trials[:PRUNE_EXACT_LIMIT]:
                if not trial_state.feasible:
                    continue
                current_state = trial_state
                current_order = list(trial_state.order)
                accepted = True
                break
            if not accepted:
                break

        if current_state.fitness >= candidate.fitness:
            return candidate
        improved = self._candidate_from_state(candidate.chromosome, current_state)
        self._candidate_cache[improved.chromosome] = improved
        return improved

    def _prune_elites(self, population: list[Stage1Candidate], started_at: float) -> list[Stage1Candidate]:
        limit = max(0, int(self.scenario.stage1.elite_prune_count))
        if limit <= 0:
            return population

        feasible_indices = [idx for idx, candidate in enumerate(population) if candidate.feasible]
        feasible_indices.sort(key=lambda idx: population[idx].fitness)
        for idx in feasible_indices[:limit]:
            if self._time_exceeded(started_at):
                break
            population[idx] = self._prune_candidate(population[idx])
        return population

    def run(self) -> Stage1Result:
        ga = self.scenario.stage1.ga
        started_at = time.perf_counter()
        self._started_at = started_at
        timed_out = False
        history: list[dict[str, float | int | bool | None]] = []

        def record_history(generation: int, population: list[Stage1Candidate], archive: list[Stage1Candidate], stall_value: int) -> None:
            population_best = min(population, key=lambda item: item.fitness) if population else None
            best_feasible = archive[0] if archive else None
            history.append(
                {
                    "generation": generation,
                    "feasible_in_population": sum(1 for item in population if item.feasible),
                    "feasible_archive_size": len(archive),
                    "stall_count": stall_value,
                    "population_best_feasible": (population_best.feasible if population_best is not None else False),
                    "population_best_violation": (population_best.violation if population_best is not None else None),
                    "population_best_sr_theta_c": (population_best.sr_theta_c if population_best is not None else None),
                    "population_best_eta_cap": (population_best.eta_cap if population_best is not None else None),
                    "population_best_avg_hot_coverage": (population_best.avg_hot_coverage if population_best is not None else None),
                    "population_best_activation_count": (population_best.activation_count if population_best is not None else None),
                    "population_best_window_count": (population_best.window_count if population_best is not None else None),
                    "best_feasible_violation": (best_feasible.violation if best_feasible is not None else None),
                    "best_feasible_sr_theta_c": (best_feasible.sr_theta_c if best_feasible is not None else None),
                    "best_feasible_eta_cap": (best_feasible.eta_cap if best_feasible is not None else None),
                    "best_feasible_avg_hot_coverage": (best_feasible.avg_hot_coverage if best_feasible is not None else None),
                    "best_feasible_activation_count": (best_feasible.activation_count if best_feasible is not None else None),
                    "best_feasible_window_count": (best_feasible.window_count if best_feasible is not None else None),
                }
            )

        population: list[Stage1Candidate] = []
        for chromosome in self._initial_population():
            if self._time_exceeded(started_at):
                timed_out = True
                break
            population.append(self._evaluate_chromosome(chromosome))
        population = self._prune_elites(population, started_at)
        feasible_archive: list[Stage1Candidate] = self._update_archive([], population)

        best_progress_fitness: tuple[float, ...] | None = (
            feasible_archive[0].fitness
            if feasible_archive
            else (population[0].fitness if population else None)
        )
        stall = 0
        generations = 0
        record_history(0, population, feasible_archive, stall)

        for generation in range(1, ga.max_generations + 1):
            if self._time_exceeded(started_at):
                timed_out = True
                break

            generations = generation
            population.sort(key=lambda item: item.fitness)
            new_population = population[: ga.elite_count]

            while len(new_population) < min(ga.population_size, ga.elite_count + ga.immigrant_count):
                if self._time_exceeded(started_at):
                    timed_out = True
                    break
                immigrant = self._rcl_chromosome() if self.random.random() < 0.5 else self._random_chromosome()
                new_population.append(self._evaluate_chromosome(immigrant))

            while not timed_out and len(new_population) < ga.population_size:
                if self._time_exceeded(started_at):
                    timed_out = True
                    break
                parent_a = self._tournament_select(population)
                parent_b = self._tournament_select(population)
                if self.random.random() < ga.crossover_probability:
                    child = self._prefix_crossover(parent_a.chromosome, parent_b.chromosome)
                else:
                    better = min((parent_a, parent_b), key=lambda item: item.fitness)
                    child = list(better.chromosome)
                if self.random.random() < ga.mutation_probability:
                    child = self._mutate(child)
                new_population.append(self._evaluate_chromosome(child))

            if new_population:
                population = self._prune_elites(new_population, started_at)
                feasible_archive = self._update_archive(feasible_archive, population)

            current_progress_fitness: tuple[float, ...] | None = (
                feasible_archive[0].fitness
                if feasible_archive
                else (population[0].fitness if population else None)
            )
            if current_progress_fitness is not None and current_progress_fitness != best_progress_fitness:
                best_progress_fitness = current_progress_fitness
                stall = 0
            elif current_progress_fitness is not None:
                stall += 1

            record_history(generation, population, feasible_archive, stall)

            if timed_out or stall >= ga.stall_generations:
                break

        population.sort(key=lambda item: item.fitness)
        final_archive = feasible_archive[: ga.top_m]
        if final_archive and not timed_out:
            final_archive = [self._prune_candidate(candidate) for candidate in final_archive]
            final_archive = self._update_archive([], final_archive)

        return Stage1Result(
            best_feasible=final_archive,
            population_best=population[0] if population else None,
            generations=generations,
            used_feedback=True,
            timed_out=timed_out,
            elapsed_seconds=time.perf_counter() - started_at,
            history=history,
        )


def run_stage1(scenario: Scenario, seed: int | None = None) -> Stage1Result:
    return Stage1GA(scenario, seed=seed).run()
