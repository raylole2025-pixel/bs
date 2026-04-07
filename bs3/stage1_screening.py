from __future__ import annotations

import math
from collections import defaultdict

from .models import CandidateWindow, Scenario

EPS = 1e-9


def _density(window: CandidateWindow, t_pre: float) -> float:
    value = float(window.value or 0.0)
    return value / max(window.duration + t_pre, EPS)


def screen_candidate_windows(
    scenario: Scenario,
    *,
    pool_size: int = 450,
    block_seconds: float = 900.0,
) -> list[CandidateWindow]:
    if pool_size <= 0 or len(scenario.candidate_windows) <= pool_size:
        scenario.metadata["stage1_screening"] = {
            "candidate_window_count_raw": len(scenario.candidate_windows),
            "candidate_window_count_screened": len(scenario.candidate_windows),
            "screen_pool_size": max(pool_size, len(scenario.candidate_windows)),
            "screen_block_seconds": block_seconds,
            "screen_metric": "density_noop",
        }
        return list(scenario.candidate_windows)

    blocks: dict[int, list[CandidateWindow]] = defaultdict(list)
    for window in scenario.candidate_windows:
        block_idx = int(math.floor(window.start / max(block_seconds, EPS)))
        blocks[block_idx].append(window)

    ordered_blocks = sorted(blocks)
    ranked_blocks = {
        block_idx: sorted(
            items,
            key=lambda item: (
                _density(item, scenario.stage1.t_pre),
                float(item.value or 0.0),
                item.duration,
                -item.start,
            ),
            reverse=True,
        )
        for block_idx, items in blocks.items()
    }

    base_quota = pool_size // len(ordered_blocks)
    remainder = pool_size % len(ordered_blocks)

    selected_ids: set[str] = set()
    selected: list[CandidateWindow] = []
    next_extra: list[tuple[float, int, CandidateWindow]] = []

    for block_idx in ordered_blocks:
        ranked = ranked_blocks[block_idx]
        quota = min(len(ranked), base_quota)
        for item in ranked[:quota]:
            if item.window_id in selected_ids:
                continue
            selected_ids.add(item.window_id)
            selected.append(item)

        if quota < len(ranked):
            candidate = ranked[quota]
            next_extra.append((_density(candidate, scenario.stage1.t_pre), block_idx, candidate))

    next_extra.sort(reverse=True)
    for _, block_idx, item in next_extra:
        if len(selected) >= pool_size or remainder <= 0:
            break
        if item.window_id in selected_ids:
            continue
        selected_ids.add(item.window_id)
        selected.append(item)
        remainder -= 1

    if len(selected) < pool_size:
        leftovers: list[CandidateWindow] = []
        for block_idx in ordered_blocks:
            for item in ranked_blocks[block_idx]:
                if item.window_id not in selected_ids:
                    leftovers.append(item)
        leftovers.sort(
            key=lambda item: (
                _density(item, scenario.stage1.t_pre),
                float(item.value or 0.0),
                item.duration,
                -item.start,
            ),
            reverse=True,
        )
        for item in leftovers:
            if len(selected) >= pool_size:
                break
            selected_ids.add(item.window_id)
            selected.append(item)

    selected.sort(key=lambda item: (item.start, item.end, item.window_id))
    scenario.metadata["stage1_screening"] = {
        "candidate_window_count_raw": len(scenario.candidate_windows),
        "candidate_window_count_screened": len(selected),
        "screen_pool_size": pool_size,
        "screen_block_seconds": block_seconds,
        "screen_metric": "density",
    }
    scenario.candidate_windows = selected
    return selected
